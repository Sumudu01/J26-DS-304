import json
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Literal, Optional

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting


TimeSeriesInterval = Literal["day", "week", "month"]


class JobPostingTimeSeriesAgent:
    """Aggregate stored, dated postings into a trend series and skill frequencies."""

    @classmethod
    def get_series(
        cls,
        db: Session,
        *,
        days: int = 730,
        interval: TimeSeriesInterval = "month",
        today: Optional[date] = None,
    ) -> Dict[str, Any]:
        if not 1 <= days <= 730:
            raise ValueError("days must be between 1 and 730")
        if interval not in {"day", "week", "month"}:
            raise ValueError(f"Unsupported time-series interval: {interval}")

        end_date = today or datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)
        postings = (
            db.query(
                JobPosting.posted_timestamp,
                JobPosting.skills_extracted,
                JobPosting.skills_processed,
            )
            .filter(
                JobPosting.posted_timestamp.isnot(None),
                JobPosting.posted_timestamp >= datetime.combine(
                    start_date, datetime.min.time(), tzinfo=timezone.utc
                ),
                JobPosting.posted_timestamp < datetime.combine(
                    end_date + timedelta(days=1),
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ),
            )
            .all()
        )
        latest_postings = (
            db.query(JobPosting)
            .filter(
                JobPosting.posted_timestamp.isnot(None),
                JobPosting.posted_timestamp >= datetime.combine(
                    start_date, datetime.min.time(), tzinfo=timezone.utc
                ),
                JobPosting.posted_timestamp < datetime.combine(
                    end_date + timedelta(days=1),
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ),
            )
            .order_by(
                desc(JobPosting.posted_timestamp),
                desc(JobPosting.created_at),
            )
            .limit(10)
            .all()
        )
        undated_jobs = (
            db.query(func.count(JobPosting.id))
            .filter(JobPosting.posted_timestamp.is_(None))
            .scalar()
            or 0
        )

        points: Dict[date, Dict[str, Any]] = {}
        cursor = start_date
        while cursor <= end_date:
            key = cls._bucket_start(cursor, interval)
            points.setdefault(key, {"job_count": 0, "skills": Counter()})
            cursor += timedelta(days=1)

        for posting in postings:
            posted_at = posting.posted_timestamp
            posted_day = (
                posted_at.astimezone(timezone.utc).date()
                if posted_at.tzinfo
                else posted_at.date()
            )
            bucket = cls._bucket_start(posted_day, interval)
            point = points.setdefault(bucket, {"job_count": 0, "skills": Counter()})
            point["job_count"] += 1
            point["skills"].update(
                cls._extract_skills(posting.skills_extracted, posting.skills_processed)
            )

        serialized_points = [
            {
                "period_start": period.isoformat(),
                "job_count": values["job_count"],
                "top_skills": [
                    {"skill": skill, "count": count}
                    for skill, count in values["skills"].most_common(10)
                ],
            }
            for period, values in sorted(points.items())
        ]
        return {
            "interval": interval,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_dated_jobs": sum(point["job_count"] for point in serialized_points),
            "undated_jobs_excluded": undated_jobs,
            "points": serialized_points,
            "latest_postings": [
                {
                    "job_id": posting.job_id,
                    "title": posting.title,
                    "company": posting.company,
                    "source": posting.source,
                    "source_platforms": posting.source_platforms,
                    "source_jobs": posting.source_jobs,
                    "job_link": posting.job_link,
                    "posted_date_text": posting.posted_date_text,
                    "posted_timestamp": posting.posted_timestamp,
                    "description_raw": posting.description_raw,
                    "skills_extracted": posting.get_skills(),
                }
                for posting in latest_postings
            ],
        }

    @staticmethod
    def _bucket_start(day: date, interval: TimeSeriesInterval) -> date:
        if interval == "week":
            return day - timedelta(days=day.weekday())
        if interval == "month":
            return day.replace(day=1)
        return day

    @staticmethod
    def _extract_skills(
        extracted_json: Optional[str],
        processed_json: Optional[str],
    ) -> list[str]:
        skills: set[str] = set()
        if extracted_json:
            try:
                extracted = json.loads(extracted_json)
            except (TypeError, ValueError):
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
                processed = {}
            if isinstance(processed, dict):
                canonical_skills = processed.get("canonical_skills", [])
                if isinstance(canonical_skills, list):
                    skills.update(
                        skill.strip()
                        for skill in canonical_skills
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
        return sorted(skills)
