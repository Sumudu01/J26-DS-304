import logging
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.components.forecasting.agents.insight_generation_agent import InsightGenerationAgent
from app.models.job_posting import JobPosting

logger = logging.getLogger("emploreralk.services.forecasting")


class ForecastingService:
    """Build skill-demand forecasts from the dated job postings in the database."""

    @classmethod
    def get_demand_insights(
        cls,
        db: Session,
        target_year: int,
        *,
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        current_day = today or datetime.now(timezone.utc).date()
        current_period_start = current_day - timedelta(days=364)
        previous_period_end = current_period_start - timedelta(days=1)
        previous_period_start = current_day - timedelta(days=729)

        rows = (
            db.query(
                JobPosting.skills_extracted,
                JobPosting.skills_processed,
                JobPosting.posted_timestamp,
            )
            .filter(JobPosting.status.in_(["extracted", "processed"]))
            .all()
        )

        current_counts: Counter[str] = Counter()
        previous_counts: Counter[str] = Counter()
        current_job_ids = set()
        previous_job_ids = set()

        for row_index, row in enumerate(rows):
            posted_date = row.posted_timestamp
            if posted_date is None:
                continue
            if isinstance(posted_date, datetime):
                if posted_date.tzinfo is not None:
                    posted_date = posted_date.astimezone(timezone.utc).date()
                else:
                    posted_date = posted_date.date()
            elif not isinstance(posted_date, date):
                continue

            if current_period_start <= posted_date <= current_day:
                counts = current_counts
                job_ids = current_job_ids
            elif previous_period_start <= posted_date <= previous_period_end:
                counts = previous_counts
                job_ids = previous_job_ids
            else:
                continue

            skills = cls._extract_skills(row.skills_extracted, row.skills_processed)
            if not skills:
                continue
            job_ids.add(row_index)
            counts.update(skills)

        skill_names = current_counts.keys() | previous_counts.keys()
        comparison_counts = {
            skill: {
                "current": current_counts.get(skill, 0),
                "previous": previous_counts.get(skill, 0),
            }
            for skill in skill_names
        }
        return InsightGenerationAgent.generate(
            comparison_counts,
            target_year=target_year,
            current_period_start=current_period_start,
            current_period_end=current_day,
            previous_period_start=previous_period_start,
            previous_period_end=previous_period_end,
            current_period_jobs=len(current_job_ids),
            previous_period_jobs=len(previous_job_ids),
        )

    @staticmethod
    def _extract_skills(extracted_json: Optional[str], processed_json: Optional[str]) -> set[str]:
        import json

        skills: set[str] = set()
        if extracted_json:
            try:
                extracted = json.loads(extracted_json)
            except (TypeError, ValueError):
                logger.warning("Skipping malformed extracted skills JSON in demand forecast")
                extracted = []
            if isinstance(extracted, list):
                skills.update(
                    skill.strip()
                    for skill in extracted
                    if isinstance(skill, str) and skill.strip()
                )

        if processed_json:
            try:
                processed = json.loads(processed_json)
            except (TypeError, ValueError):
                logger.warning("Skipping malformed processed skills JSON in demand forecast")
                processed = {}
            if isinstance(processed, dict):
                normalized = processed.get("canonical_skills", [])
                if isinstance(normalized, list):
                    skills.update(
                        skill.strip()
                        for skill in normalized
                        if isinstance(skill, str) and skill.strip()
                    )
                normalized_items = processed.get("normalized_items", [])
                if isinstance(normalized_items, list):
                    skills.update(
                        item["canonical_name"].strip()
                        for item in normalized_items
                        if isinstance(item, dict)
                        and isinstance(item.get("canonical_name"), str)
                        and item["canonical_name"].strip()
                    )
        return skills