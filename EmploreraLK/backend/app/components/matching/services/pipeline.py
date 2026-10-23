"""Candidate-to-job retrieval and contextual reranking orchestration."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable, Sequence
import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any, Optional

from sqlalchemy.exc import SQLAlchemyError

from app.components.matching.models.embeddings import (
    INFERENCE_LOCK,
    embed_processed_job_postings,
    embedding_config,
    generate_embedding,
    prepare_candidate_text,
)

logger = logging.getLogger("emploreralk.components.matching")
from app.components.matching.models.reranking import rerank_jobs
from app.components.matching.services.reasoning import reason_about_matches
from app.components.matching.models.retrieval import DenseJobIndex

_processed_index_cache: dict[Optional[int], DenseJobIndex] = {}
_processed_index_lock = threading.Lock()
_index_build_lock = threading.Lock()
_index_build_waiters: dict[Optional[int], threading.Event] = {}

# ── Recommendation cache ─────────────────────────────────────────────────────
# Page changes, refreshes and frontend retries used to re-run BGE-M3 and the
# Cross-Encoder from scratch, and parallel requests competed for the CPU.
# Model inference is serialised by INFERENCE_LOCK (torch already uses every
# core per call), and results are cached per candidate text + index, so an
# unchanged profile is served instantly and any profile/CV edit misses.
_RESULT_CACHE_TTL_SECONDS = 15 * 60
_RESULT_CACHE_MAX_ENTRIES = 128
_result_cache: "OrderedDict[tuple[Any, ...], tuple[float, Any]]" = OrderedDict()
_result_cache_lock = threading.Lock()


def _cache_get(key: tuple[Any, ...]) -> Any:
    with _result_cache_lock:
        entry = _result_cache.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if time.monotonic() - stored_at > _RESULT_CACHE_TTL_SECONDS:
            del _result_cache[key]
            return None
        _result_cache.move_to_end(key)
        return value


def _cache_put(key: tuple[Any, ...], value: Any) -> None:
    with _result_cache_lock:
        _result_cache[key] = (time.monotonic(), value)
        _result_cache.move_to_end(key)
        while len(_result_cache) > _RESULT_CACHE_MAX_ENTRIES:
            _result_cache.popitem(last=False)

# ── Disk-persistence helpers ─────────────────────────────────────────────────
# The index is saved under EMPLORERALK_MODEL_CACHE (same dir as the model).
# Two files are written:
#   jobs.faiss           — the FAISS binary
#   jobs.mapping.json    — job IDs + dimension (written by DenseJobIndex.save)
#   jobs.signature.json  — the processed-job signature used as the cache key,
#                          so we can detect when jobs have changed on disk load.

_FAISS_SUBDIR = "faiss_job_index"


def _faiss_index_dir() -> Optional[Path]:
    """Return the directory where the FAISS index is persisted, or None."""
    cache_root = os.getenv("EMPLORERALK_MODEL_CACHE")
    if not cache_root:
        return None
    return Path(cache_root) / _FAISS_SUBDIR


def _save_index_to_disk(index: DenseJobIndex, signature: tuple[Any, ...]) -> None:
    """Persist the FAISS index and its signature to disk."""
    index_dir = _faiss_index_dir()
    if index_dir is None:
        return
    try:
        index.save(index_dir)
        sig_path = index_dir / "jobs.signature.json"
        sig_path.write_text(
            json.dumps(
                {"signature": list(signature), "embedding": embedding_config()},
                default=str,
            ),
            encoding="utf-8",
        )
        logger.info("FAISS job index persisted to %s", index_dir)
    except Exception as exc:
        logger.warning("Could not persist FAISS index to disk: %s", exc)


def _read_saved_signature(index_dir: Path) -> Optional[dict[str, Any]]:
    sig_path = index_dir / "jobs.signature.json"
    if not (sig_path.exists() and (index_dir / "jobs.faiss").exists()
            and (index_dir / "jobs.mapping.json").exists()):
        return None
    saved = json.loads(sig_path.read_text(encoding="utf-8"))
    return saved if isinstance(saved, dict) else None


def _reusable_vectors(signature: tuple[Any, ...]) -> dict[Any, list[float]]:
    """Vectors from the saved index for jobs whose updated_at is unchanged.

    Lets a stale index be refreshed by embedding only new or edited jobs
    instead of re-encoding the whole dataset.  Nothing is reused when the
    embedding settings (model, token cap) differ from the saved ones.
    """
    index_dir = _faiss_index_dir()
    if index_dir is None:
        return {}
    try:
        saved = _read_saved_signature(index_dir)
        if not saved or saved.get("embedding") != embedding_config():
            return {}
        saved_stamps = {row[0]: row[1] for row in saved.get("signature", [])}
        current = {job_id: stamp for job_id, stamp in signature}
        vectors = DenseJobIndex.load(index_dir).vectors_by_id()
        return {
            job_id: vector for job_id, vector in vectors.items()
            if job_id in current and saved_stamps.get(job_id) == current[job_id]
        }
    except Exception as exc:
        logger.warning("Could not reuse saved FAISS vectors: %s", exc)
        return {}


def _load_index_from_disk(
    signature: tuple[Any, ...],
    db: Any,
) -> Optional[DenseJobIndex]:
    """Try to load a previously-saved FAISS index if its signature still matches.

    After loading the bare FAISS index we re-attach the live JobPosting ORM
    objects from the DB so downstream code can access job fields.  This DB
    query fetches only the IDs we already know about — it is fast because it
    uses a simple IN filter.
    """
    index_dir = _faiss_index_dir()
    if index_dir is None:
        return None

    try:
        saved = _read_saved_signature(index_dir)
        if saved is None:
            return None
        # Saved signature is a list of [id, updated_at] pairs; convert back to tuple-of-tuples
        saved_sig = tuple(tuple(row) for row in saved.get("signature", []))
        if saved_sig != signature or saved.get("embedding") != embedding_config():
            logger.info(
                "Saved FAISS index is stale (jobs or embedding settings changed) — will refresh."
            )
            return None

        index = DenseJobIndex.load(index_dir)
        # Re-attach live ORM objects so job fields are accessible
        from app.models.job_posting import JobPosting

        saved_ids = list(index.job_ids)
        jobs = db.query(JobPosting).filter(JobPosting.id.in_(saved_ids)).all()
        index.attach_jobs(jobs)
        logger.info(
            "Loaded FAISS job index from disk (%d jobs).", index.size
        )
        return index
    except Exception as exc:
        logger.warning("Could not load FAISS index from disk: %s", exc)
        return None


# ── Pipeline helpers ─────────────────────────────────────────────────────────

def _release_db_connection(db: Any) -> None:
    """Return the SQLAlchemy connection to the pool before long ML work."""
    if db is None or not callable(getattr(db, "rollback", None)):
        return
    try:
        db.rollback()
    except SQLAlchemyError as error:
        logger.warning(
            "Database session rollback failed before ML work (%s); invalidating connection.",
            error,
        )
        invalidate = getattr(db, "invalidate", None)
        if callable(invalidate):
            try:
                invalidate()
            except Exception:
                pass
        else:
            try:
                db.connection().invalidate()
            except Exception:
                pass
        try:
            db.rollback()
        except Exception:
            pass


def _load_seeker(
    db: Any,
    *,
    candidate_id: Optional[int] = None,
    email: Optional[str] = None,
) -> Any:
    if db is None or not callable(getattr(db, "query", None)):
        raise ValueError("db must be an active SQLAlchemy session")
    if candidate_id is None and not email:
        raise ValueError("candidate_id or email must be provided")

    from app.models.user import User

    query = db.query(User).filter(User.role == "seeker")
    if candidate_id is not None:
        query = query.filter(User.id == candidate_id)
    else:
        query = query.filter(User.email == email)
    candidate = query.first()
    if candidate is None:
        raise LookupError("candidate was not found")
    return candidate


def _candidate_profile(db: Any, candidate: Any) -> dict[str, Any]:
    """Merge the seeker's profile row with their parsed CV, if one was uploaded.

    The User model only stores roles and skills; qualifications, education,
    projects and work experience live in CandidateCV.parsed_data.  Without
    this merge prepare_candidate_text() never sees the CV.
    """
    get_skills = getattr(candidate, "get_skills_list", None)
    profile: dict[str, Any] = {
        "current_role": getattr(candidate, "current_role", None),
        "target_role": getattr(candidate, "target_role", None),
        "skills": get_skills() if callable(get_skills) else getattr(candidate, "skills", None),
    }
    try:
        from app.models.candidate_cv import CandidateCV

        record = db.query(CandidateCV).filter(CandidateCV.user_id == candidate.id).first()
    except SQLAlchemyError as error:
        logger.warning("Could not load CV for candidate %s: %s", candidate.id, error)
        record = None
    if record is not None:
        parsed = record.get_parsed_data()
        if parsed:
            profile["cv"] = parsed
    return profile


def _eligible_job_signature(db: Any, limit: Optional[int]) -> tuple[Any, ...]:
    """Build a cache key from *eligible* processed job IDs and their timestamps.

    Only jobs that will actually be indexed (those whose skills_processed
    contains at least one canonical skill, a normalized item, OR a non-empty
    description that prepare_job_text() can use) are included.  Skipping the
    5 empty-skill jobs that appear in the broader processed set means the
    signature stays stable after new jobs are added with proper skill data,
    preventing spurious full rebuilds.
    """
    from app.models.job_posting import JobPosting

    query = (
        db.query(JobPosting.id, JobPosting.updated_at, JobPosting.skills_processed,
                 JobPosting.skills_extracted, JobPosting.description_raw,
                 JobPosting.title)
        .filter(
            JobPosting.status == "processed",
            JobPosting.skills_processed.isnot(None),
        )
        .order_by(JobPosting.id)
    )
    if limit is not None:
        query = query.limit(limit)

    entries = []
    for row in query.all():
        sp_raw = row.skills_processed or "{}"
        try:
            import json as _json
            sp = _json.loads(sp_raw) if isinstance(sp_raw, str) else sp_raw
        except Exception:
            sp = {}
        if not isinstance(sp, dict):
            sp = {}
        has_normalized = bool(sp.get("canonical_skills") or sp.get("normalized_items"))
        # Fallback: job is still useful if it has a description or extracted skills
        has_fallback = bool(
            (row.description_raw and row.description_raw.strip())
            or (row.skills_extracted and row.skills_extracted.strip())
            or (row.title and row.title.strip())
        )
        if has_normalized or has_fallback:
            entries.append((row.id, str(row.updated_at)))
    return tuple(entries)


def _add_reasoning(
    candidate_text: str,
    ranked_jobs: list[dict[str, Any]],
    *,
    llm_client: Any,
    llm_model: Optional[str],
    reasoning_top_k: Optional[int],
) -> list[dict[str, Any]]:
    if reasoning_top_k is None:
        selected = ranked_jobs
    else:
        if reasoning_top_k < 1:
            raise ValueError("reasoning_top_k must be greater than zero")
        selected = ranked_jobs[:reasoning_top_k]
    # The domain-context line is query expansion for retrieval, not something
    # the candidate stated; keep it out of the LLM so it is not cited as a skill.
    stated_text = "\n".join(
        line for line in candidate_text.splitlines()
        if not line.startswith("Domain context for target role:")
    )
    reasoned = reason_about_matches(
        stated_text or candidate_text,
        selected,
        client=llm_client,
        model=llm_model,
    )
    reasoning_by_id = {item.get("job_id"): item.get("llm_reasoning") for item in reasoned}
    return [
        {**item, "llm_reasoning": reasoning_by_id.get(item.get("job_id"))}
        for item in ranked_jobs
    ]


def build_processed_job_index(
    db: Any,
    *,
    limit: Optional[int] = None,
    embedding_model: Any = None,
) -> Optional[DenseJobIndex]:
    """Build (or restore from disk) a dense FAISS index of processed jobs.

    Load order
    ----------
    1. In-memory cache  — keyed on ``limit`` only (not on the job signature).
                          Once an index is loaded into memory it is reused for
                          the entire server process lifetime, regardless of
                          whether the DB grows.  A server restart is required
                          to pick up newly processed jobs.
    2. Disk cache       — loads the saved FAISS binary (~milliseconds) and
                          re-attaches live ORM objects from a fast DB IN query.
                          Accepted even when the DB has grown since the index
                          was built: the index still contains all jobs that were
                          eligible at build time and will serve results while a
                          background rebuild is NOT triggered solely by new jobs.
                          A mismatch only forces a rebuild when explicitly needed.
    3. Full rebuild     — only triggered if no valid disk index exists.
                          Protected by a process-level lock keyed on ``limit``
                          alone so concurrent callers (warm-up thread + early
                          API request) always share the same waiter and only
                          ONE rebuild runs at a time.

    Signature mismatch handling
    ---------------------------
    The signature is used to detect genuinely stale disk indexes (e.g. after
    the server process restarts with a completely different set of jobs).
    However, a growing DB (new jobs added by the collection pipeline) is
    handled by the rebuild triggered at the NEXT server restart, not by
    invalidating the in-memory cache mid-session.  This prevents the repeated-
    rebuild loop: once an index is in memory it stays there for the session.
    """
    # ── 1. In-memory cache  (keyed on limit only) ─────────────────────────────
    with _processed_index_lock:
        cached_index = _processed_index_cache.get(limit)
        if cached_index is not None:
            return cached_index

    # ── 2. Disk cache ─────────────────────────────────────────────────────────
    # Compute signature NOW, once, to check the disk index.
    signature = _eligible_job_signature(db, limit)
    if not signature:
        return None

    disk_index = _load_index_from_disk(signature, db)
    if disk_index is not None:
        with _processed_index_lock:
            _processed_index_cache[limit] = disk_index
        return disk_index

    # ── 3. Full rebuild — only ONE thread per (limit,) at a time ─────────────
    # The lock is keyed on `limit` only, not on the signature.  This means
    # that even if the warm-up thread and an API request computed slightly
    # different signatures (because the DB grew between calls), they share the
    # same waiter and the second caller simply waits for the first to finish
    # rather than starting a parallel rebuild.
    with _index_build_lock:
        waiter = _index_build_waiters.get(limit)
        if waiter is None:
            waiter = threading.Event()
            _index_build_waiters[limit] = waiter
            is_builder = True
        else:
            is_builder = False

    if not is_builder:
        waiter.wait(timeout=1800)
        with _processed_index_lock:
            return _processed_index_cache.get(limit)

    try:
        logger.info(
            "Building FAISS job index from scratch (no valid disk cache found)..."
        )
        job_embeddings = embed_processed_job_postings(
            db,
            limit=limit,
            model=embedding_model,
            reuse=_reusable_vectors(signature),
        )
        if not job_embeddings:
            return None
        index = DenseJobIndex.build(job_embeddings)
        with _processed_index_lock:
            _processed_index_cache[limit] = index
        # Save to disk using the signature computed at the START of this build.
        # This records exactly which jobs were indexed, so the next restart can
        # determine whether a rebuild is truly needed.
        _save_index_to_disk(index, signature)
        return index
    finally:
        waiter.set()
        with _index_build_lock:
            _index_build_waiters.pop(limit, None)


def recommend_jobs(
    candidate_profile: Any,
    *,
    job_embeddings: Optional[Iterable[tuple[Any, Sequence[float]]]] = None,
    job_index: Optional[DenseJobIndex] = None,
    embedding_model: Any = None,
    cross_encoder: Any = None,
    llm_client: Any = None,
    llm_model: Optional[str] = None,
    reasoning_top_k: Optional[int] = 3,
    top_k: int = 10,
    rerank_top_k: Optional[int] = None,
) -> list[dict[str, Any]]:
    """Run candidate preparation, BGE-M3 retrieval, and Cross-Encoder reranking."""
    if top_k < 1:
        raise ValueError("top_k must be greater than zero")
    if rerank_top_k is not None and rerank_top_k < 1:
        raise ValueError("rerank_top_k must be greater than zero")

    candidate_text = prepare_candidate_text(candidate_profile)
    candidate_embedding = generate_embedding(candidate_text, model=embedding_model)
    index = job_index
    if index is None:
        if job_embeddings is None:
            raise ValueError("job_embeddings or job_index must be provided")
        job_embeddings_list = list(job_embeddings)
        if not job_embeddings_list:
            return []
        index = DenseJobIndex.build(job_embeddings_list)

    retrieved = index.search(candidate_embedding, top_k=top_k)
    if not retrieved:
        return []
    ranked_jobs = rerank_jobs(
        candidate_text,
        retrieved,
        model=cross_encoder,
        top_k=rerank_top_k,
    )
    return _add_reasoning(
        candidate_text,
        ranked_jobs,
        llm_client=llm_client,
        llm_model=llm_model,
        reasoning_top_k=reasoning_top_k,
    )


def recommend_jobs_from_db(
    db: Any,
    *,
    candidate_id: Optional[int] = None,
    email: Optional[str] = None,
    job_index: Optional[DenseJobIndex] = None,
    embedding_model: Any = None,
    cross_encoder: Any = None,
    llm_client: Any = None,
    llm_model: Optional[str] = None,
    reasoning_top_k: Optional[int] = 3,
    top_k: int = 10,
    rerank_top_k: Optional[int] = None,
    job_limit: Optional[int] = None,
    page: int = 1,
    page_size: int = 12,
) -> dict[str, Any]:
    """Recommend processed jobs for a seeker loaded from the existing database.

    Returns a dict with:
        ``items``           — ranked results for the requested page
        ``total_available`` — total eligible jobs in the FAISS index
        ``total_ranked``    — jobs in the reranked pool that pages slice from
        ``page``            — current page number (1-indexed)
        ``page_size``       — items per page
    """
    candidate = _load_seeker(db, candidate_id=candidate_id, email=email)
    candidate_text = prepare_candidate_text(_candidate_profile(db, candidate))
    _release_db_connection(db)

    if top_k < 1:
        raise ValueError("top_k must be greater than zero")
    if page < 1:
        raise ValueError("page must be greater than zero")
    if page_size < 1:
        raise ValueError("page_size must be greater than zero")
    if rerank_top_k is not None and rerank_top_k < 1:
        raise ValueError("rerank_top_k must be greater than zero")

    index = job_index
    if index is None:
        index = build_processed_job_index(db, limit=job_limit, embedding_model=embedding_model)
    if index is None:
        return {"items": [], "total_available": 0, "total_ranked": 0, "page": page, "page_size": page_size}

    total_available = index.size

    # Retrieve enough candidates from FAISS to cover all pages up to the
    # requested one, then slice after reranking.  This preserves ranking
    # quality: we always score the same top-N pool and paginate within it.
    retrieve_n = max(top_k, page * page_size)
    retrieve_n = min(retrieve_n, total_available)

    # Injected models/clients (tests, experiments) bypass the shared cache.
    cacheable = embedding_model is None and cross_encoder is None and llm_client is None
    pool_key = (
        hashlib.sha256(candidate_text.encode("utf-8")).hexdigest(),
        id(index), index.size, retrieve_n, rerank_top_k,
    )
    page_key = (*pool_key, page, page_size, reasoning_top_k, llm_model)

    with INFERENCE_LOCK:
        page_results = _cache_get(page_key) if cacheable else None
        ranked_jobs = _cache_get(pool_key) if cacheable else None
        if ranked_jobs is None:
            candidate_embedding = generate_embedding(candidate_text, model=embedding_model)
            retrieved = index.search(candidate_embedding, top_k=retrieve_n)
            ranked_jobs = rerank_jobs(
                candidate_text,
                retrieved,
                model=cross_encoder,
                top_k=rerank_top_k,
            )
            if cacheable:
                _cache_put(pool_key, ranked_jobs)

    if page_results is None:
        # Paginate: slice the ranked list into the requested page window
        start = (page - 1) * page_size
        end   = start + page_size
        page_results = _add_reasoning(
            candidate_text,
            ranked_jobs[start:end],
            llm_client=llm_client,
            llm_model=llm_model,
            reasoning_top_k=reasoning_top_k,
        )
        if cacheable:
            _cache_put(page_key, page_results)

    return {
        "items": page_results,
        "total_available": total_available,
        "total_ranked": len(ranked_jobs),
        "page": page,
        "page_size": page_size,
    }
