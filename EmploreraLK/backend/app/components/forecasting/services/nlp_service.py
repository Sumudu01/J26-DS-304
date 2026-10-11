import logging
import threading
import time
from typing import Any, Dict, List, Optional
from collections import Counter
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.core.database import SessionLocal
from app.models.job_posting import JobPosting, NLPExtractionRun
from app.schemas.nlp_extraction import (
    NLPExtractionGoal,
    NLPExtractionRunStatus,
    TextSkillExtractionResponse,
)
from app.components.forecasting.agents.nlp_extraction_agent import NLPExtractionAgent

logger = logging.getLogger("emploreralk.services.nlp")

_ACTIVE_NLP_RUNS: Dict[str, Dict[str, Any]] = {}


class NLPService:
    """
    Orchestration service for the Autonomous NLP Extraction Agent.
    Manages background tasks, direct text processing, and skill analytics.
    """

    @classmethod
    def run_agent_in_background(cls, run_id: str, goal: NLPExtractionGoal) -> None:
        """Background worker thread for processing large batches."""
        db: Session = SessionLocal()
        try:
            logger.info("Background thread started for NLP extraction run %s", run_id)
            agent = NLPExtractionAgent(db=db)
            status_report = agent.execute_goal(goal, run_id=run_id)
            _ACTIVE_NLP_RUNS[run_id] = {
                "status": status_report.status,
                "total_processed": status_report.total_processed,
                "skills_extracted_count": status_report.skills_extracted_count,
                "report": status_report.model_dump(),
            }
            logger.info("Background NLP extraction run %s finished with status: %s", run_id, status_report.status)
        except Exception as e:
            logger.error("Error in background NLP run %s: %s", run_id, e)
            _ACTIVE_NLP_RUNS[run_id] = {
                "status": "failed",
                "error": str(e),
            }
        finally:
            db.close()

    @classmethod
    def trigger_extraction(
        cls,
        goal: NLPExtractionGoal,
        db: Session
    ) -> NLPExtractionRunStatus:
        """
        Trigger NLP skill extraction on collected job postings.
        Can run synchronously or asynchronously in the background.
        """
        run_id = f"nlp_run_{int(time.time())}"

        if goal.background:
            _ACTIVE_NLP_RUNS[run_id] = {
                "status": "running",
                "total_processed": 0,
                "skills_extracted_count": 0,
            }
            thread = threading.Thread(
                target=cls.run_agent_in_background,
                args=(run_id, goal),
                daemon=True
            )
            thread.start()

            return NLPExtractionRunStatus(
                run_id=run_id,
                status="running",
                total_processed=0,
                skills_extracted_count=0,
                unique_skills_count=0,
                execution_summary={"message": "NLP Extraction Agent running in background"}
            )
        else:
            agent = NLPExtractionAgent(db=db)
            return agent.execute_goal(goal, run_id=run_id)

    @classmethod
    def extract_from_raw_text(
        cls,
        text: str,
        title: str = ""
    ) -> TextSkillExtractionResponse:
        """Ad-hoc text and skill extraction from arbitrary job descriptions."""
        result = NLPExtractionAgent.extract_skills_from_text(text=text, title=title)
        return TextSkillExtractionResponse(
            skills=result["skills"],
            skills_by_category=result["skills_by_category"],
            seniority_level=result["seniority_level"],
            experience_years_min=result["experience_years_min"],
            education_level=result["education_level"],
            confidence=result["confidence"],
        )

    @classmethod
    def get_run_status(cls, run_id: str, db: Session) -> Optional[NLPExtractionRunStatus]:
        """Fetch status and telemetry report for an NLP extraction run."""
        db_run = db.query(NLPExtractionRun).filter(NLPExtractionRun.run_id == run_id).first()
        if db_run:
            summary = db_run.get_summary()
            return NLPExtractionRunStatus(
                run_id=db_run.run_id,
                status=db_run.status,
                total_processed=db_run.total_processed,
                skills_extracted_count=db_run.skills_extracted_count,
                unique_skills_count=summary.get("unique_skills_count", 0),
                started_at=db_run.started_at,
                completed_at=db_run.completed_at,
                top_skills=summary.get("top_skills"),
                execution_summary=summary,
                error_message=db_run.error_message,
            )

        if run_id in _ACTIVE_NLP_RUNS:
            mem = _ACTIVE_NLP_RUNS[run_id]
            return NLPExtractionRunStatus(
                run_id=run_id,
                status=mem.get("status", "running"),
                total_processed=mem.get("total_processed", 0),
                skills_extracted_count=mem.get("skills_extracted_count", 0),
                unique_skills_count=0,
                execution_summary=mem.get("report"),
                error_message=mem.get("error"),
            )

        return None

    @classmethod
    def get_all_runs(cls, db: Session, limit: int = 20) -> List[NLPExtractionRunStatus]:
        """List historical NLP extraction runs."""
        runs = (
            db.query(NLPExtractionRun)
            .order_by(desc(NLPExtractionRun.started_at))
            .limit(limit)
            .all()
        )
        results = []
        for r in runs:
            summary = r.get_summary()
            results.append(
                NLPExtractionRunStatus(
                    run_id=r.run_id,
                    status=r.status,
                    total_processed=r.total_processed,
                    skills_extracted_count=r.skills_extracted_count,
                    unique_skills_count=summary.get("unique_skills_count", 0),
                    started_at=r.started_at,
                    completed_at=r.completed_at,
                    top_skills=summary.get("top_skills"),
                    execution_summary=summary,
                    error_message=r.error_message,
                )
            )
        return results

    @classmethod
    def get_global_skill_distribution(cls, db: Session, limit: int = 30) -> Dict[str, Any]:
        """Compute aggregated skill frequencies across all processed postings in DB."""
        jobs = db.query(JobPosting.skills_extracted).filter(JobPosting.skills_extracted.isnot(None)).all()
        counter = Counter()
        for j in jobs:
            if not j[0]:
                continue
            try:
                parsed = j.get_skills() if hasattr(j, "get_skills") else None
                if not parsed:
                    import json
                    parsed = json.loads(j[0])
                if isinstance(parsed, list):
                    for s in parsed:
                        counter[s] += 1
            except Exception:
                pass

        total_postings_analyzed = len(jobs)
        top_skills = [{"skill": s, "frequency": count} for s, count in counter.most_common(limit)]

        return {
            "total_postings_analyzed": total_postings_analyzed,
            "unique_skills_identified": len(counter),
            "top_skills": top_skills,
        }
