import json
import re
from collections import Counter
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.components.skill_gap.candidate_collection_service import (
	collect_run,
	create_collection_run,
	get_run_response,
)
from app.components.skill_gap.models import CandidateCollectionRun, CandidateProfile
from app.components.skill_gap.schemas import (
	CandidateCollectionRequest,
	CandidateCollectionRunResponse,
	CandidateListResponse,
	SkillGapAnalysisRequest,
	SkillGapAnalysisResponse,
)
from app.models.job_posting import JobPosting
from app.models.user import User

router = APIRouter(prefix="/skill-gap", tags=["Skill Gap Candidate Collection"])


def _require_seeker(user: User) -> None:
	if user.role != "seeker":
		raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Seeker access is required.")


@router.post("", response_model=SkillGapAnalysisResponse, summary="Analyze a seeker's skill gap")
def analyze_skill_gap(
	payload: SkillGapAnalysisRequest,
	db: Session = Depends(get_db),
	user: User = Depends(get_current_user),
) -> dict[str, Any]:
	_require_seeker(user)
	role = payload.target_role.strip()
	role_terms = [term for term in re.split(r"[/,\s]+", role) if len(term) > 1]
	conditions = [JobPosting.title.ilike(f"%{role}%"), JobPosting.search_keyword.ilike(f"%{role}%")]
	conditions.extend(
		field.ilike(f"%{term}%")
		for term in role_terms
		for field in (JobPosting.title, JobPosting.search_keyword)
	)
	postings = (
		db.query(JobPosting)
		.filter(JobPosting.skills_extracted.isnot(None), or_(*conditions))
		.order_by(desc(JobPosting.created_at))
		.limit(200)
		.all()
	)

	target_skill_counts: Counter[str] = Counter()
	target_skill_names: dict[str, str] = {}
	for posting in postings:
		for skill in posting.get_skills():
			name = str(skill).strip()
			if name:
				key = name.casefold()
				target_skill_names.setdefault(key, name)
				target_skill_counts[key] += 1
	target_keys = [key for key, _ in target_skill_counts.most_common(15)]
	target_skills = [target_skill_names[key] for key in target_keys]

	profile_skills = set(user.get_skills_list())
	profiles = db.query(CandidateProfile.skills_json).filter(CandidateProfile.owner_user_id == user.id).all()
	for row in profiles:
		try:
			stored_skills = json.loads(row.skills_json or "[]")
		except (TypeError, ValueError):
			stored_skills = []
		profile_skills.update(str(skill).strip() for skill in stored_skills if str(skill).strip())
	profile_skills.update(skill.strip() for skill in payload.skills if skill and skill.strip())
	profile_skill_names = {skill.casefold(): skill for skill in profile_skills}

	matching_keys = [key for key in target_keys if key in profile_skill_names]
	missing_keys = [key for key in target_keys if key not in profile_skill_names]
	matching_skills = [profile_skill_names[key] for key in matching_keys]
	missing_skills = [target_skill_names[key] for key in missing_keys]
	match_percentage = round(len(matching_keys) / len(target_keys) * 100) if target_keys else 0

	nodes = [
		{"id": "candidate", "name": "Your profile", "group": "candidate"},
		{"id": "target", "name": role, "group": "target"},
	]
	links = []
	for key in target_keys:
		node_id = f"skill:{key}"
		group = "matched_skill" if key in matching_keys else "missing_skill"
		nodes.append({"id": node_id, "name": target_skill_names[key], "group": group})
		links.append({"source": "target", "target": node_id})
		if key in matching_keys:
			links.append({"source": "candidate", "target": node_id})

	roadmap = []
	if missing_skills:
		midpoint = (len(missing_skills) + 1) // 2
		roadmap = [
			{"title": "Build core skills", "skills": missing_skills[:midpoint]},
		]
		if missing_skills[midpoint:]:
			roadmap.append({"title": "Apply and deepen skills", "skills": missing_skills[midpoint:]})

	return {
		"target_role": role,
		"match_percentage": match_percentage,
		"matching_skills": matching_skills,
		"missing_skills": missing_skills,
		"target_skills": target_skills,
		"graph_data": {"nodes": nodes, "links": links},
		"skill_roadmap": roadmap,
	}


@router.post(
	"/candidates/collect",
	response_model=CandidateCollectionRunResponse,
	status_code=status.HTTP_202_ACCEPTED,
	summary="Collect candidate details from public profiles",
)
def collect_candidates(
	payload: CandidateCollectionRequest,
	background_tasks: BackgroundTasks,
	db: Session = Depends(get_db),
	user: User = Depends(get_current_user),
) -> dict:
	_require_seeker(user)
	run = create_collection_run(db, payload.profile_urls, user.id)
	background_tasks.add_task(collect_run, run.run_id, payload.profile_urls)
	return get_run_response(run)


@router.get(
	"/candidate-collections/{run_id}",
	response_model=CandidateCollectionRunResponse,
	summary="Get candidate collection status",
)
def get_candidate_collection_status(
	run_id: str,
	db: Session = Depends(get_db),
	user: User = Depends(get_current_user),
) -> dict:
	_require_seeker(user)
	run = db.query(CandidateCollectionRun).filter(
		CandidateCollectionRun.run_id == run_id,
		CandidateCollectionRun.owner_user_id == user.id,
	).first()
	if not run:
		raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate collection run not found.")
	return get_run_response(run)


@router.get(
	"/candidates",
	response_model=CandidateListResponse,
	summary="List stored candidate profiles",
)
def list_candidates(
	query: str | None = Query(None, description="Search candidate name, headline, or skills"),
	limit: int = Query(50, ge=1, le=200),
	offset: int = Query(0, ge=0),
	db: Session = Depends(get_db),
	user: User = Depends(get_current_user),
) -> dict:
	_require_seeker(user)
	candidates_query = db.query(CandidateProfile).filter(CandidateProfile.owner_user_id == user.id)
	if query:
		term = f"%{query.strip()}%"
		candidates_query = candidates_query.filter(
			(CandidateProfile.full_name.ilike(term))
			| (CandidateProfile.headline.ilike(term))
			| (CandidateProfile.skills_json.ilike(term))
		)
	total = candidates_query.count()
	candidates = candidates_query.order_by(CandidateProfile.collected_at.desc()).offset(offset).limit(limit).all()
	return {"total": total, "items": [candidate.to_dict() for candidate in candidates]}
