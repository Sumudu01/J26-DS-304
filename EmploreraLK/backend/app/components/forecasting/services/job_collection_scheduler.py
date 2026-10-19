import logging
import threading
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.models.job_posting import DataCollectionRun
from app.schemas.job_posting import AgentCollectionGoal
from app.schemas.skill_processing import SkillProcessingGoal
from app.components.forecasting.services.scraping_service import ScrapingService
from app.components.forecasting.services.skill_processing_service import (
    SkillProcessingService,
)
from app.components.forecasting.agents.job_posting_time_series_agent import (
    JobPostingTimeSeriesAgent,
)
from app.components.forecasting.services.forecasting_service import ForecastingService

logger = logging.getLogger("emploreralk.services.job_collection_scheduler")


class LiveJobCollectionScheduler:
    """Run one coordinated multi-source collection cycle at a fixed interval."""

    def __init__(self, interval_minutes: int = 15):
        if interval_minutes < 1:
            raise ValueError("interval_minutes must be at least 1")
        self.interval_seconds = interval_minutes * 60
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="live-job-collection-scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info(
            "Live job collection scheduler started (every %d minutes).",
            self.interval_seconds // 60,
        )

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            self._collect_once()
            delay = max(0, self.interval_seconds - (time.monotonic() - started))
            if self._stop_event.wait(delay):
                break

    def _collect_once(self) -> None:
        slot = int(time.time() // self.interval_seconds)
        run_id = f"scheduled_{slot}"
        db = SessionLocal()
        try:
            stale_before = datetime.now(timezone.utc) - timedelta(hours=24)
            stale_runs = (
                db.query(DataCollectionRun)
                .filter(
                    DataCollectionRun.status.in_(["pending", "running"]),
                    DataCollectionRun.run_id.like("scheduled_%"),
                    DataCollectionRun.started_at < stale_before,
                )
                .all()
            )
            for stale_run in stale_runs:
                stale_run.status = "failed"
                stale_run.error_message = "Scheduled collection expired without completion."
                stale_run.completed_at = datetime.now(timezone.utc)
            if stale_runs:
                db.commit()

            active_run = (
                db.query(DataCollectionRun.run_id)
                .filter(
                    DataCollectionRun.status.in_(["pending", "running"]),
                    DataCollectionRun.run_id.like("scheduled_%"),
                )
                .first()
            )
            if active_run:
                logger.info(
                    "Skipping scheduled slot %s because run %s is still active.",
                    run_id,
                    active_run[0],
                )
                return

            run = DataCollectionRun(
                run_id=run_id,
                source="LinkedIn,TopJobs.lk,Rooster.jobs",
                target_keywords="Information Technology",
                target_location="sri lanka",
                target_count=50,
                collected_count=0,
                duplicate_count=0,
                status="pending",
            )
            db.add(run)
            try:
                db.commit()
            except IntegrityError:
                db.rollback()
                logger.info("Scheduled collection slot %s was already claimed.", run_id)
                return

            goal = AgentCollectionGoal(
                keywords="Information Technology",
                location="sri lanka",
                max_jobs=50,
                sources=["LinkedIn", "TopJobs", "Rooster.jobs"],
                fetch_full_description=True,
                background=False,
            )
            result = ScrapingService.trigger_collection(goal=goal, db=db, run_id=run_id)
            skill_status = SkillProcessingService.trigger_processing(
                goal=SkillProcessingGoal(limit=50, background=False),
                db=db,
            )
            time_series = JobPostingTimeSeriesAgent.get_series(
                db,
                days=730,
                interval="month",
            )
            try:
                forecast = ForecastingService.train_and_store(
                    db,
                    horizon_months=36,
                )
                forecast_summary = {
                    "status": "completed",
                    "run_id": forecast["run_id"],
                    "best_model": forecast["best_model"],
                    "series_count": len(forecast["series"]),
                }
            except (RuntimeError, ValueError) as exc:
                logger.warning(
                    "Forecast refresh after collection %s was not completed: %s",
                    run_id,
                    exc,
                )
                forecast_summary = {
                    "status": "unavailable",
                    "error": str(exc),
                }
            run = db.query(DataCollectionRun).filter_by(run_id=run_id).one()
            summary = result.execution_summary or {}
            summary["skill_processing"] = {
                "status": skill_status.status,
                "run_id": skill_status.run_id,
            }
            summary["time_series"] = {
                "status": "completed",
                "total_dated_jobs": time_series["total_dated_jobs"],
                "interval": time_series["interval"],
                "points": len(time_series["points"]),
            }
            summary["demand_forecast"] = forecast_summary
            run.set_summary(summary)
            db.commit()
            logger.info(
                "Scheduled four-agent collection %s finished with status %s.",
                run_id,
                result.status,
            )
        except Exception:
            db.rollback()
            logger.exception("Scheduled job collection %s failed.", run_id)
            failed_run = db.query(DataCollectionRun).filter_by(run_id=run_id).first()
            if failed_run:
                failed_run.status = "failed"
                failed_run.error_message = "Scheduled collection failed; see backend logs."
                failed_run.completed_at = datetime.now(timezone.utc)
                db.commit()
        finally:
            db.close()
