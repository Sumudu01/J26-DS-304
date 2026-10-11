import logging
import threading
import time
from typing import Any, Dict, List, Optional
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import SessionLocal
from app.models.job_posting import JobPosting, SkillProcessingRun
from app.schemas.skill_processing import (
    SkillProcessingGoal,
    SkillProcessingRunStatus,
    AdHocSkillNormalizationRequest,
    AdHocSkillNormalizationResponse,
    SkillCoOccurrenceResponse,
    SkillCoOccurrenceItem,
    TaxonomyTreeResponse,
)
from app.components.forecasting.agents.skill_processing_agent import (
    SkillProcessingAgent,
    TAXONOMY_TREE,
)

logger = logging.getLogger("emploreralk.services.skill_processing")

_ACTIVE_SKILL_RUNS: Dict[str, Dict[str, Any]] = {}


class SkillProcessingService:
    """
    Orchestration service for the Autonomous Skill Processing Agent.
    Manages background worker threads, synchronous batch executions,
    ad-hoc skill normalization, run telemetry lookups, and taxonomy analytics.
    """

    @classmethod
    def run_agent_in_background(cls, run_id: str, goal: SkillProcessingGoal) -> None:
        """Background worker thread for processing large job batches."""
        db: Session = SessionLocal()
        try:
            logger.info("Background worker started for skill processing run %s", run_id)
            agent = SkillProcessingAgent(db=db)
            status_report = agent.execute_goal(goal, run_id=run_id)
            _ACTIVE_SKILL_RUNS[run_id] = {
                "status": status_report.status,
                "total_processed": status_report.total_processed,
                "skills_normalized_count": status_report.skills_normalized_count,
                "report": status_report.model_dump(),
            }
            logger.info("Background skill run %s finished with status: %s", run_id, status_report.status)
        except Exception as e:
            logger.error("Error in background skill run %s: %s", run_id, e)
            _ACTIVE_SKILL_RUNS[run_id] = {
                "status": "failed",
                "error": str(e),
            }
        finally:
            db.close()

    @classmethod
    def trigger_processing(
        cls,
        goal: SkillProcessingGoal,
        db: Session
    ) -> SkillProcessingRunStatus:
        """Trigger automated skill normalization across database job postings."""
        run_id = f"skill_run_{int(time.time())}"

        if goal.background:
            _ACTIVE_SKILL_RUNS[run_id] = {
                "status": "running",
                "total_processed": 0,
                "skills_normalized_count": 0,
                "started_at": time.time(),
            }
            worker_thread = threading.Thread(
                target=cls.run_agent_in_background,
                args=(run_id, goal),
                daemon=False,
                name=f"skill-proc-{run_id}"
            )
            worker_thread.start()

            return SkillProcessingRunStatus(
                run_id=run_id,
                status="running",
                total_processed=0,
                skills_normalized_count=0,
                unique_canonical_skills_count=0,
                execution_summary={
                    "message": "Autonomous Skill Processing Agent deployed asynchronously.",
                    "batch_size": goal.batch_size,
                    "fuzzy_threshold": goal.fuzzy_threshold,
                    "enable_implication": goal.enable_implication,
                }
            )

        # Synchronous execution
        agent = SkillProcessingAgent(db=db)
        return agent.execute_goal(goal, run_id=run_id)

    @classmethod
    def normalize_adhoc_skills(
        cls,
        payload: AdHocSkillNormalizationRequest
    ) -> AdHocSkillNormalizationResponse:
        """Normalize an arbitrary list of raw skill strings on demand."""
        agent = SkillProcessingAgent()
        result = agent.process_skills_for_posting(
            raw_skills=payload.skills,
            job_title=payload.job_title or "",
            fuzzy_threshold=payload.fuzzy_threshold,
            enable_implication=payload.enable_implication,
        )

        return AdHocSkillNormalizationResponse(
            normalized_skills=result.normalized_skills,
            canonical_skills=result.canonical_skills,
            implied_skills=result.implied_skills,
            core_skills=result.core_skills,
            domain_breakdown=result.skills_by_domain,
            category_breakdown=result.skills_by_category,
            total_canonical_count=len(result.canonical_skills),
        )

    @classmethod
    def get_run_status(cls, run_id: str, db: Session) -> Optional[SkillProcessingRunStatus]:
        """Retrieve telemetry and execution report for a specific skill run."""
        # Check active in-memory cache
        if run_id in _ACTIVE_SKILL_RUNS:
            mem = _ACTIVE_SKILL_RUNS[run_id]
            if "report" in mem:
                return SkillProcessingRunStatus(**mem["report"])
            return SkillProcessingRunStatus(
                run_id=run_id,
                status=mem.get("status", "running"),
                total_processed=mem.get("total_processed", 0),
                skills_normalized_count=mem.get("skills_normalized_count", 0),
                unique_canonical_skills_count=0,
                execution_summary={"source": "in_memory_worker"},
                error_message=mem.get("error"),
            )

        # Look up in PostgreSQL
        record = db.query(SkillProcessingRun).filter(SkillProcessingRun.run_id == run_id).first()
        if not record:
            return None

        summary = record.get_summary()
        return SkillProcessingRunStatus(
            run_id=record.run_id,
            status=record.status,
            total_processed=record.total_processed,
            skills_normalized_count=record.skills_normalized_count,
            unique_canonical_skills_count=record.unique_canonical_skills_count,
            started_at=record.started_at,
            completed_at=record.completed_at,
            top_canonical_skills=summary.get("top_canonical_skills"),
            domain_distribution=summary.get("domain_distribution"),
            execution_summary=summary,
            error_message=record.error_message,
        )

    @classmethod
    def get_all_runs(cls, db: Session, limit: int = 20) -> List[SkillProcessingRunStatus]:
        """List historical autonomous skill processing agent runs."""
        runs = db.query(SkillProcessingRun).order_by(desc(SkillProcessingRun.started_at)).limit(limit).all()
        results: List[SkillProcessingRunStatus] = []
        for r in runs:
            summary = r.get_summary()
            results.append(
                SkillProcessingRunStatus(
                    run_id=r.run_id,
                    status=r.status,
                    total_processed=r.total_processed,
                    skills_normalized_count=r.skills_normalized_count,
                    unique_canonical_skills_count=r.unique_canonical_skills_count,
                    started_at=r.started_at,
                    completed_at=r.completed_at,
                    top_canonical_skills=summary.get("top_canonical_skills"),
                    domain_distribution=summary.get("domain_distribution"),
                    execution_summary=summary,
                    error_message=r.error_message,
                )
            )
        return results

    @classmethod
    def get_skill_co_occurrences(
        cls,
        skill_name: str,
        db: Session,
        limit: int = 15
    ) -> SkillCoOccurrenceResponse:
        """Find co-occurring skills and cluster relationships for a target skill."""
        agent = SkillProcessingAgent(db=db)
        co_list = agent.get_co_occurring_skills(skill_name=skill_name, limit=limit)

        # Get canonical name of target
        norm = agent.normalize_single_skill(skill_name)
        canonical = norm[0] if norm else skill_name.strip()

        # Count total postings containing this skill
        jobs = db.query(JobPosting).filter(JobPosting.skills_processed.isnot(None)).all()
        total_postings = 0
        for j in jobs:
            data = j.get_processed_skills()
            if canonical in data.get("canonical_skills", []):
                total_postings += 1

        items = [
            SkillCoOccurrenceItem(
                skill=item["skill"],
                co_occurrence_count=item["co_occurrence_count"],
                strength=item["strength"]
            )
            for item in co_list
        ]

        return SkillCoOccurrenceResponse(
            target_skill=skill_name,
            canonical_name=canonical,
            total_postings_with_skill=total_postings,
            co_occurring_skills=items,
        )

    @classmethod
    def get_taxonomy_tree(cls) -> TaxonomyTreeResponse:
        """Return the complete hierarchical taxonomy structure."""
        agent = SkillProcessingAgent()
        data = agent.get_taxonomy_tree()
        return TaxonomyTreeResponse(
            total_domains=data["total_domains"],
            total_categories=data["total_categories"],
            total_canonical_skills=data["total_canonical_skills"],
            tree=data["tree"],
        )
