import logging
import threading
import time
from datetime import datetime, timezone
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

    @staticmethod
    def _source_filter_condition(source: str) -> Any:
        escaped_source = source.strip().replace('"', '\\"')
        return or_(
            JobPosting.source.ilike(f"%{source.strip()}%"),
            JobPosting.raw_metadata.ilike(
                f'%"source_platforms"%"{escaped_source}"%'
            ),
            JobPosting.raw_metadata.ilike(
                f'%"source_jobs"%"{escaped_source}"%'
            ),
        )

    @staticmethod
    def _extract_collected_jobs(db: Session, job_ids: List[str]) -> int:
        """Persist descriptions and extracted skills for postings from this collection."""
        if not job_ids:
            return 0

        from app.components.forecasting.agents.nlp_extraction_agent import NLPExtractionAgent

        extractor = NLPExtractionAgent(db=db)
        processed_count = 0
        failures = []
        for job_id in job_ids:
            try:
                job = db.query(JobPosting).filter(JobPosting.job_id == job_id).first()
                if job is None:
                    logger.error("Collected job %s was not found for NLP extraction.", job_id)
                    failures.append(job_id)
                    continue
                extractor.process_job_posting(job)
                db.commit()
                processed_count += 1
            except Exception as error:
                db.rollback()
                failures.append(job_id)
                logger.exception("Failed NLP extraction for collected job %s: %s", job_id, error)

        if failures:
            failed_ids = ", ".join(failures)
            raise RuntimeError(
                f"NLP extraction failed for {len(failures)} collected job posting(s): {failed_ids}"
            )
        return processed_count

    @classmethod
    def process_collected_jobs(
        cls,
        db: Session,
        report: AgentExecutionReport,
    ) -> Dict[str, Any]:
        """Run extraction after scraping and keep the collection run status accurate."""
        db_run = db.query(DataCollectionRun).filter(
            DataCollectionRun.run_id == report.run_id
        ).first()
        if db_run:
            db_run.status = "running"
            db_run.error_message = None
            db_run.completed_at = None
            db.commit()

        report_data = report.to_dict()
        try:
            processed_count = cls._extract_collected_jobs(db, report.collected_job_ids)
        except Exception as error:
            db.rollback()
            db_run = db.query(DataCollectionRun).filter(
                DataCollectionRun.run_id == report.run_id
            ).first()
            if db_run:
                report_data["nlp_extraction"] = {
                    "status": "failed",
                    "error": str(error),
                }
                db_run.status = "failed"
                db_run.error_message = str(error)
                db_run.completed_at = datetime.now(timezone.utc)
                db_run.set_summary(report_data)
                db.commit()
            raise

        report_data["nlp_extraction"] = {
            "status": "completed",
            "processed_count": processed_count,
        }
        db_run = db.query(DataCollectionRun).filter(
            DataCollectionRun.run_id == report.run_id
        ).first()
        if db_run:
            db_run.status = report.status
            db_run.error_message = None
            db_run.completed_at = datetime.now(timezone.utc)
            db_run.set_summary(report_data)
            db.commit()
        return report_data

    @classmethod
    def run_agent_in_background(cls, run_id: str, goal: AgentCollectionGoal) -> None:
        """Worker function running in background thread with a dedicated DB session."""
        db: Session = SessionLocal()
        try:
            logger.info("Background thread started for agent run %s", run_id)
            agent = LinkedInDataCollectionAgent(db=db)
            report = agent.execute_goal(goal, run_id=run_id)
            report_data = cls.process_collected_jobs(db, report)
            _ACTIVE_RUNS[run_id] = {
                "status": report.status,
                "collected_count": report.jobs_collected,
                "duplicate_count": report.duplicates_skipped,
                "cross_platform_duplicates_merged": report.cross_platform_duplicates_merged,
                "report": report_data,
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
        db: Session,
        run_id: Optional[str] = None,
    ) -> AgentRunStatus:
        """
        Trigger an autonomous agent data collection session across configured job portals.
        If goal.background is True, starts a background thread and returns immediately.
        Otherwise executes synchronously.
        """
        sources_label = ",".join(goal.sources) if goal.sources else "LinkedIn,TopJobs,Rooster.jobs"
        run_id = run_id or f"run_{int(time.time())}_{goal.keywords[:4].lower().replace(' ', '_')}"

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
            report_data = cls.process_collected_jobs(db, report)

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
                execution_summary=report_data,
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
            query = query.filter(cls._source_filter_condition(source))

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
    def get_recommended_jobs(
        cls,
        db: Session,
        target_role: Optional[str] = None,
        user_skills: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 20,
        source_filter: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Return personalized job postings matched to the user's target_role and skills.
        When keyword is provided, search titles, skills, and descriptions for that term
        instead of restricting to the profile target role.
        Results are ranked by skill overlap then recency.
        """
        search_term = (keyword or "").strip()
        role_terms = []
        if not search_term and target_role:
            role_terms = [
                t.strip()
                for t in target_role.replace("/", " ").replace(",", " ").split()
                if len(t.strip()) > 2
            ]
        query = db.query(JobPosting)

        if source_filter:
            query = query.filter(cls._source_filter_condition(source_filter))

        if search_term:
            tokens = [t for t in search_term.replace("/", " ").replace(",", " ").split() if len(t) > 1] or [search_term]
            title_conditions = []
            for term in tokens:
                term_like = f"%{term}%"
                title_conditions.extend([
                    JobPosting.title.ilike(term_like),
                    JobPosting.search_keyword.ilike(term_like),
                    JobPosting.description_raw.ilike(term_like),
                    JobPosting.skills_extracted.ilike(term_like),
                    JobPosting.company.ilike(term_like),
                    JobPosting.location.ilike(term_like),
                ])
            query = query.filter(or_(*title_conditions))
        elif role_terms:
            title_conditions = []
            for term in role_terms:
                term_like = f"%{term}%"
                title_conditions.append(JobPosting.title.ilike(term_like))
                title_conditions.append(JobPosting.search_keyword.ilike(term_like))
                title_conditions.append(JobPosting.description_raw.ilike(term_like))
            query = query.filter(or_(*title_conditions))

        total = query.count()
        offset = (page - 1) * page_size
        raw_items = (
            query.order_by(desc(JobPosting.posted_timestamp), desc(JobPosting.created_at))
            .offset(offset)
            .limit(page_size * 3)  # Over-fetch for client-side relevance ranking
            .all()
        )

        # Score each job by skill overlap with user's skills
        user_skills_lower = set(s.lower().strip() for s in (user_skills or []))

        def _score(job: JobPosting) -> int:
            if not user_skills_lower:
                return 0
            extracted = job.get_skills()
            job_skills_lower = set(s.lower().strip() for s in extracted)
            return len(user_skills_lower & job_skills_lower)

        scored = sorted(raw_items, key=_score, reverse=True)[:page_size]

        def _serialize(job: JobPosting) -> Dict[str, Any]:
            skills = job.get_skills()
            overlap = list(user_skills_lower & set(s.lower() for s in skills)) if user_skills_lower else []
            metadata = job.get_metadata()
            source_platforms = metadata.get("source_platforms", [])
            if not isinstance(source_platforms, list):
                source_platforms = []
            source_platforms = list(dict.fromkeys(
                [str(source) for source in source_platforms if source]
                + [job.source]
            ))
            source_jobs = metadata.get("source_jobs", [])
            if not isinstance(source_jobs, list):
                source_jobs = []
            source_jobs = [
                source_job for source_job in source_jobs
                if isinstance(source_job, dict)
                and source_job.get("source")
                and source_job.get("job_link")
            ]
            if not source_jobs:
                source_jobs = [{
                    "source": job.source,
                    "job_id": job.job_id,
                    "job_link": job.job_link,
                }]
            description_image_urls = metadata.get("description_image_urls", [])
            if isinstance(description_image_urls, str):
                description_image_urls = [description_image_urls]
            if not isinstance(description_image_urls, list):
                description_image_urls = []
            return {
                "id": job.id,
                "job_id": job.job_id,
                "title": job.title,
                "company": job.company,
                "location": job.location or "Sri Lanka",
                "job_link": job.job_link,
                "source": job.source,
                "source_platforms": source_platforms,
                "source_jobs": source_jobs,
                "posted_date_text": job.posted_date_text,
                "posted_timestamp": job.posted_timestamp.isoformat() if job.posted_timestamp else None,
                "skills_extracted": skills,
                "skill_overlap": overlap,
                "skill_match_count": len(overlap),
                "seniority_level": job.seniority_level,
                "experience_years_min": job.experience_years_min,
                "description_snippet": (job.description_raw or "")[:300].strip() + "…" if job.description_raw else None,
                "description_text": job.description_raw,
                "description_image_urls": description_image_urls,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }

        return {
            "target_role": target_role,
            "keyword": search_term or None,
            "total_matched": total,
            "page": page,
            "page_size": page_size,
            "items": [_serialize(j) for j in scored],
        }

    @classmethod
    def trigger_full_pipeline(
        cls,
        target_role: str,
        location: str = "Sri Lanka",
        max_jobs: int = 50,
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Trigger the full 4-agent pipeline in background:
        1. Data Collection Agent (LinkedIn + TopJobs + Rooster.jobs)
        2. NLP Extraction Agent
        3. Skill Processing Agent
        4. Job Posting Time-Series Agent
        Returns a pipeline run summary with individual run IDs.
        """
        from app.schemas.job_posting import AgentCollectionGoal
        from app.schemas.nlp_extraction import NLPExtractionGoal
        from app.schemas.skill_processing import SkillProcessingGoal
        from app.components.forecasting.services.nlp_service import NLPService
        from app.components.forecasting.services.skill_processing_service import SkillProcessingService
        from app.components.forecasting.services.forecasting_service import ForecastingService
        from app.components.forecasting.agents.job_posting_time_series_agent import (
            JobPostingTimeSeriesAgent,
        )

        import time
        pipeline_id = f"pipeline_{int(time.time())}_{target_role[:6].lower().replace(' ', '_')}"
        results: Dict[str, Any] = {"pipeline_id": pipeline_id, "target_role": target_role, "stages": {}}
        collection_run_id: Optional[str] = None

        # Stage 1 — Data Collection (including full descriptions for NLP)
        try:
            collection_goal = AgentCollectionGoal(
                keywords=target_role,
                location=location,
                max_jobs=max_jobs,
                background=True,
                sources=["LinkedIn", "TopJobs", "Rooster.jobs"],
                fetch_full_description=True,
                min_delay=1.0,   # Reduced from 2.0 — still polite but 2x faster
                max_delay=2.5,   # Reduced from 4.0
            )
            _db = db or SessionLocal()
            collection_status = cls.trigger_collection(goal=collection_goal, db=_db)
            results["stages"]["data_collection"] = {
                "run_id": collection_status.run_id,
                "status": collection_status.status,
            }
            collection_run_id = collection_status.run_id
            if db is None:
                _db.close()
        except Exception as e:
            logger.error("Pipeline stage 1 (data collection) failed: %s", e)
            results["stages"]["data_collection"] = {"status": "failed", "error": str(e)}

        # Stage 2 — NLP Extraction (background thread)
        def _run_nlp_then_skills():
            import time as _t
            collection_deadline = time.monotonic() + 1800
            while (
                collection_run_id
                and _ACTIVE_RUNS.get(collection_run_id, {}).get("status") == "running"
                and time.monotonic() < collection_deadline
            ):
                _t.sleep(1)

            collection_state = _ACTIVE_RUNS.get(collection_run_id or "", {})
            if collection_state.get("status") == "running":
                logger.error(
                    "Collection run %s did not finish before NLP OCR processing began.",
                    collection_run_id,
                )
                return
            if collection_state.get("status") == "failed":
                logger.error(
                    "Collection run %s failed; continuing NLP with previously saved postings.",
                    collection_run_id,
                )

            _db2 = SessionLocal()
            try:
                nlp_goal = NLPExtractionGoal(batch_size=max_jobs, background=False)
                nlp_status = NLPService.trigger_extraction(goal=nlp_goal, db=_db2)
                results["stages"]["nlp_extraction"] = {
                    "run_id": nlp_status.run_id,
                    "status": nlp_status.status,
                }
            except Exception as e2:
                logger.error("Pipeline stage 2 (NLP) failed: %s", e2)
                results["stages"]["nlp_extraction"] = {"status": "failed", "error": str(e2)}
            finally:
                _db2.close()

            # Stage 3 — Skill Processing
            _db3 = SessionLocal()
            try:
                skill_goal = SkillProcessingGoal(limit=max_jobs, background=False)
                skill_status = SkillProcessingService.trigger_processing(goal=skill_goal, db=_db3)
                results["stages"]["skill_processing"] = {
                    "run_id": skill_status.run_id,
                    "status": skill_status.status,
                }
            except Exception as e3:
                logger.error("Pipeline stage 3 (skill processing) failed: %s", e3)
                results["stages"]["skill_processing"] = {"status": "failed", "error": str(e3)}
            try:
                time_series = JobPostingTimeSeriesAgent.get_series(
                    _db3,
                    days=730,
                    interval="month",
                )
                results["stages"]["time_series"] = {
                    "status": "completed",
                    "total_dated_jobs": time_series["total_dated_jobs"],
                    "interval": time_series["interval"],
                    "points": len(time_series["points"]),
                }
            except Exception as e4:
                logger.exception("Pipeline stage 4 (time-series aggregation) failed: %s", e4)
                results["stages"]["time_series"] = {
                    "status": "failed",
                    "error": str(e4),
                }
            try:
                forecast = ForecastingService.train_and_store(
                    _db3,
                    horizon_months=36,
                )
                results["stages"]["demand_forecast"] = {
                    "status": "completed",
                    "run_id": forecast["run_id"],
                    "best_model": forecast["best_model"],
                    "series_count": len(forecast["series"]),
                }
            except Exception as forecast_error:
                logger.exception("Pipeline stage 5 (demand forecasting) failed")
                results["stages"]["demand_forecast"] = {
                    "status": "failed",
                    "error": str(forecast_error),
                }
            finally:
                _db3.close()

        nlp_thread = threading.Thread(target=_run_nlp_then_skills, daemon=True)
        nlp_thread.start()

        results["status"] = "running"
        results["message"] = (
            f"Full pipeline triggered for '{target_role}'. "
            "Data Collection → NLP Extraction → Skill Processing → Time-Series Analysis → "
            "Model Evaluation and Demand Forecasting running autonomously."
        )
        return results

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
