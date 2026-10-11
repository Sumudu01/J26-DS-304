import logging
import threading
import time
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func

from app.core.database import SessionLocal
from app.models.job_posting import JobPosting, DataCollectionRun
from app.schemas.job_posting import (
    AgentCollectionGoal,
    AgentRunStatus,
    JobListResponse,
    JobPostingResponse,
)
from app.components.forecasting.agents.data_collection_agent import (
    LinkedInDataCollectionAgent,
    AgentExecutionReport,
)

logger = logging.getLogger("emploreralk.services.scraping")

# In-memory registry for fast active agent run status lookups
_ACTIVE_RUNS: Dict[str, Dict[str, Any]] = {}


class ScrapingService:
    """
    Orchestration service for the Autonomous Job Data Collection Agent.
    Manages background tasks, database persistence, and API query operations.
    """

    @classmethod
    def run_agent_in_background(cls, run_id: str, goal: AgentCollectionGoal) -> None:
        """Worker function running in background thread with a dedicated DB session."""
        db: Session = SessionLocal()
        try:
            logger.info("Background thread started for agent run %s", run_id)
            agent = LinkedInDataCollectionAgent(db=db)
            report = agent.execute_goal(goal, run_id=run_id)
            _ACTIVE_RUNS[run_id] = {
                "status": report.status,
                "collected_count": report.jobs_collected,
                "duplicate_count": report.duplicates_skipped,
                "cross_platform_duplicates_merged": report.cross_platform_duplicates_merged,
                "report": report.to_dict(),
            }
            logger.info("Background agent run %s completed with status: %s", run_id, report.status)
        except Exception as e:
            logger.error("Error in background agent run %s: %s", run_id, e)
            _ACTIVE_RUNS[run_id] = {
                "status": "failed",
                "error": str(e),
            }
        finally:
            db.close()

    @classmethod
    def trigger_collection(
        cls,
        goal: AgentCollectionGoal,
        db: Session
    ) -> AgentRunStatus:
        """
        Trigger an autonomous agent data collection session across LinkedIn & TopJobs.
        If goal.background is True, starts a background thread and returns immediately.
        Otherwise executes synchronously.
        """
        sources_label = ",".join(goal.sources) if goal.sources else "LinkedIn,TopJobs"
        run_id = f"run_{int(time.time())}_{goal.keywords[:4].lower().replace(' ', '_')}"

        if goal.background:
            _ACTIVE_RUNS[run_id] = {
                "status": "running",
                "collected_count": 0,
                "duplicate_count": 0,
                "cross_platform_duplicates_merged": 0,
            }
            thread = threading.Thread(
                target=cls.run_agent_in_background,
                args=(run_id, goal),
                daemon=True
            )
            thread.start()

            return AgentRunStatus(
                run_id=run_id,
                source=sources_label,
                status="running",
                target_keywords=goal.keywords,
                target_location=goal.location,
                target_count=goal.max_jobs,
                collected_count=0,
                duplicate_count=0,
                cross_platform_duplicates_merged=0,
                execution_summary={"message": f"Agent running autonomously in background across {sources_label}"}
            )
        else:
            agent = LinkedInDataCollectionAgent(db=db)
            report: AgentExecutionReport = agent.execute_goal(goal, run_id=run_id)

            return AgentRunStatus(
                run_id=run_id,
                source=",".join(report.sources_scraped) if report.sources_scraped else sources_label,
                status=report.status,
                target_keywords=goal.keywords,
                target_location=goal.location,
                target_count=goal.max_jobs,
                collected_count=report.jobs_collected,
                duplicate_count=report.duplicates_skipped,
                cross_platform_duplicates_merged=report.cross_platform_duplicates_merged,
                execution_summary=report.to_dict(),
                error_message=report.error
            )


    @classmethod
    def get_run_status(cls, run_id: str, db: Session) -> Optional[AgentRunStatus]:
        """Fetch status and telemetry report for an agent run."""
        # Check database
        db_run = db.query(DataCollectionRun).filter(DataCollectionRun.run_id == run_id).first()
        if db_run:
            return AgentRunStatus(
                run_id=db_run.run_id,
                source=db_run.source,
                status=db_run.status,
                target_keywords=db_run.target_keywords,
                target_location=db_run.target_location,
                target_count=db_run.target_count,
                collected_count=db_run.collected_count,
                duplicate_count=db_run.duplicate_count,
                started_at=db_run.started_at,
                completed_at=db_run.completed_at,
                execution_summary=db_run.get_summary(),
                error_message=db_run.error_message
            )

        # Fallback to in-memory active cache
        if run_id in _ACTIVE_RUNS:
            mem = _ACTIVE_RUNS[run_id]
            return AgentRunStatus(
                run_id=run_id,
                source="LinkedIn",
                status=mem.get("status", "running"),
                target_keywords="",
                target_location="",
                target_count=0,
                collected_count=mem.get("collected_count", 0),
                duplicate_count=mem.get("duplicate_count", 0),
                execution_summary=mem.get("report")
            )

        return None

    @classmethod
    def get_all_runs(cls, db: Session, limit: int = 20) -> List[AgentRunStatus]:
        """Get recent agent collection runs."""
        runs = (
            db.query(DataCollectionRun)
            .order_by(desc(DataCollectionRun.started_at))
            .limit(limit)
            .all()
        )
        return [
            AgentRunStatus(
                run_id=r.run_id,
                source=r.source,
                status=r.status,
                target_keywords=r.target_keywords,
                target_location=r.target_location,
                target_count=r.target_count,
                collected_count=r.collected_count,
                duplicate_count=r.duplicate_count,
                started_at=r.started_at,
                completed_at=r.completed_at,
                execution_summary=r.get_summary(),
                error_message=r.error_message
            )
            for r in runs
        ]

    @classmethod
    def list_jobs(
        cls,
        db: Session,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        source: Optional[str] = None,
        page: int = 1,
        page_size: int = 25
    ) -> JobListResponse:
        """Search and paginate collected jobs stored in PostgreSQL."""
        query = db.query(JobPosting)

        if keyword:
            term = f"%{keyword.strip()}%"
            query = query.filter(
                or_(
                    JobPosting.title.ilike(term),
                    JobPosting.search_keyword.ilike(term),
                    JobPosting.description_raw.ilike(term),
                )
            )

        if location:
            query = query.filter(JobPosting.location.ilike(f"%{location.strip()}%"))

        if company:
            query = query.filter(JobPosting.company.ilike(f"%{company.strip()}%"))

        if source:
            query = query.filter(JobPosting.source.ilike(f"%{source.strip()}%"))

        total = query.count()
        offset = (page - 1) * page_size
        items = (
            query.order_by(desc(JobPosting.posted_timestamp), desc(JobPosting.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return JobListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[JobPostingResponse.model_validate(item) for item in items]
        )

    @classmethod
    def get_collection_statistics(cls, db: Session) -> Dict[str, Any]:
        """Summary statistics for dashboard and forecasting readiness."""
        total_jobs = db.query(func.count(JobPosting.id)).scalar() or 0
        total_runs = db.query(func.count(DataCollectionRun.id)).scalar() or 0

        # Unique companies count
        unique_companies = db.query(func.count(func.distinct(JobPosting.company))).scalar() or 0

        # Breakdown by platform source
        source_counts = (
            db.query(JobPosting.source, func.count(JobPosting.id))
            .group_by(JobPosting.source)
            .all()
        )

        # Count of postings with complete descriptions
        jobs_with_descriptions = (
            db.query(func.count(JobPosting.id))
            .filter(JobPosting.description_raw.isnot(None), JobPosting.description_raw != "")
            .scalar() or 0
        )

        # Top keywords scraped
        keyword_counts = (
            db.query(JobPosting.search_keyword, func.count(JobPosting.id))
            .group_by(JobPosting.search_keyword)
            .order_by(desc(func.count(JobPosting.id)))
            .limit(5)
            .all()
        )

        return {
            "total_jobs_collected": total_jobs,
            "jobs_with_full_descriptions": jobs_with_descriptions,
            "unique_companies": unique_companies,
            "total_agent_runs": total_runs,
            "platform_breakdown": {s or "Unknown": count for s, count in source_counts},
            "top_keywords": [{"keyword": k or "unspecified", "count": c} for k, c in keyword_counts],
            "forecasting_pipeline_status": "ready" if total_jobs > 0 else "awaiting_data",
        }

