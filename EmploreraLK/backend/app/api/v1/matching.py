from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.components.matching.models.embeddings import _job_skills, load_embedding_model, match_skills_semantically
from app.components.matching.services.pipeline import recommend_jobs_from_db
from app.models.user import User

logger = logging.getLogger("emploreralk.components.matching")

router = APIRouter(prefix="/matching", tags=["Skill Matching"])

# Startup state flags
_embedding_model_ready = threading.Event()
_faiss_index_ready = threading.Event()


def warm_embedding_model() -> None:
    """Load BGE-M3 and pre-build the FAISS job index in a background thread.

    Called from app/main.py lifespan so both the model and the index are ready
    before the first user request.  Errors are logged but never propagate.
    """
    def _load() -> None:
        try:
            logger.info("Pre-warming BGE-M3 embedding model in background...")
            embedding_model = load_embedding_model()
            _embedding_model_ready.set()
            logger.info("BGE-M3 embedding model is ready. Building FAISS index...")

            try:
                from app.components.matching.services.pipeline import build_processed_job_index
                from app.core.database import SessionLocal
                db = SessionLocal()
                try:
                    logger.info("Pre-building FAISS job index in background...")
                    index = build_processed_job_index(db, embedding_model=embedding_model)
                    if index is not None:
                        logger.info(
                            "FAISS job index ready (%d jobs). Matching endpoint now accepting requests.",
                            index.size,
                        )
                    else:
                        logger.warning(
                            "No processed jobs found - FAISS index is empty. "
                            "Matching endpoint will return empty results."
                        )
                finally:
                    db.close()
            except Exception as idx_exc:
                logger.error(
                    "FAISS index pre-build failed: %s. "
                    "Matching endpoint will attempt to build on first request.",
                    idx_exc,
                )
            finally:
                _faiss_index_ready.set()

        except Exception as exc:
            logger.error("BGE-M3 warm-up failed: %s", exc)
            _faiss_index_ready.set()

    thread = threading.Thread(target=_load, name="bge-m3-warmup", daemon=True)
    thread.start()


def _skill_matches(results: List[Dict[str, Any]], candidate_skills: List[str]) -> List[List[Dict[str, Any]]]:
	"""Exact plus BGE-M3 semantic skill matches per job; exact-only if the model fails."""
	job_skill_lists = [_job_skills(r["job"]) if r.get("job") is not None else [] for r in results]
	try:
		return match_skills_semantically(candidate_skills, job_skill_lists)
	except (RuntimeError, ValueError) as error:
		logger.warning("Semantic skill matching unavailable, using exact matches: %s", error)
		candidate_by_key = {skill.casefold(): skill for skill in candidate_skills}
		return [
			[
				{"job_skill": s, "candidate_skill": candidate_by_key[s.casefold()], "similarity": 1.0, "match_type": "exact"}
				for s in skills if s.casefold() in candidate_by_key
			]
			for skills in job_skill_lists
		]


def _job_response(result: Dict[str, Any], skill_matches: List[Dict[str, Any]]) -> Dict[str, Any]:
	job = result.get("job")
	if job is None:
		return result
	skills = _job_skills(job)
	# skill_overlap lists job skills the candidate covers by meaning, not only by
	# identical spelling; skill_match_count counts distinct candidate skills used.
	overlap = [match["job_skill"] for match in skill_matches]
	return {
		"id": job.id,
		"job_id": job.job_id,
		"title": job.title,
		"company": job.company,
		"location": job.location,
		"job_link": job.job_link,
		"posted_date_text": job.posted_date_text,
		"source": job.source,
		"description_snippet": (job.description_raw or "")[:300],
		"skills_extracted": skills,
		"skill_overlap": overlap,
		"exact_skill_overlap": [m["job_skill"] for m in skill_matches if m["match_type"] == "exact"],
		"semantic_skill_matches": [m for m in skill_matches if m["match_type"] == "semantic"],
		"skill_match_count": len({m["candidate_skill"].casefold() for m in skill_matches}),
		"retrieval_similarity_score": result.get("retrieval_similarity_score"),
		"cross_encoder_score": result.get("cross_encoder_score"),
		"final_score": result.get("final_score"),
		"reranker": result.get("reranker"),
		"rank": result.get("rank"),
		"llm_reasoning": result.get("llm_reasoning"),
	}


@router.get("/recommendations", response_model=Dict[str, Any])
def get_matching_recommendations(
	top_k: int = Query(50, ge=1, le=200),
	rerank_top_k: int = Query(50, ge=1, le=200),
	reasoning_top_k: int = Query(3, ge=1, le=12),
	page: int = Query(1, ge=1, description="1-indexed page number"),
	page_size: int = Query(12, ge=1, le=50, description="Results per page"),
	current_user: User = Depends(get_current_user),
	db: Session = Depends(get_db),
	response: Response = None,
) -> Dict[str, Any]:
	"""Run Component 4 retrieval, reranking, and optional LLM reasoning."""
	# Fast-path: model/index still warming up
	if not _faiss_index_ready.is_set():
		if response is not None:
			response.headers["Retry-After"] = "15"
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail={
				"warming": True,
				"message": (
					"The matching engine is still starting up. "
					"Please retry in a moment."
				),
			},
		)

	try:
		result = recommend_jobs_from_db(
			db,
			candidate_id=current_user.id,
			top_k=top_k,
			rerank_top_k=rerank_top_k,
			reasoning_top_k=reasoning_top_k,
			page=page,
			page_size=page_size,
		)
	except LookupError as error:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail=str(error),
		) from error
	except (RuntimeError, ValueError, SQLAlchemyError) as error:
		raise HTTPException(
			status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
			detail=f"Semantic matching is not available: {error}",
		) from error

	candidate_skills = current_user.get_skills_list()
	skill_matches = _skill_matches(result["items"], candidate_skills)
	items = [_job_response(r, m) for r, m in zip(result["items"], skill_matches)]
	total_available = result["total_available"]
	# Pages slice the reranked pool, which rerank_top_k can make smaller than the index.
	total_ranked = result.get("total_ranked", total_available)

	return {
		"total": len(items),
		"total_available": total_available,
		"total_ranked": total_ranked,
		"page": result["page"],
		"page_size": result["page_size"],
		"total_pages": max(1, -(-total_ranked // result["page_size"])),
		"items": items,
		"pipeline": "bge-m3-faiss-cross-encoder-llm",
	}
