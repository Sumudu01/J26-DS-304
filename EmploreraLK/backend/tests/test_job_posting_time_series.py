import unittest
from datetime import date, datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.components.forecasting.agents.job_posting_time_series_agent import (
    JobPostingTimeSeriesAgent,
)
from app.models.job_posting import JobPosting


class JobPostingTimeSeriesTests(unittest.TestCase):
    def test_aggregates_recent_and_historical_postings_within_two_year_window(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()
        db.add_all(
            [
                JobPosting(
                    job_id="recent",
                    title="Software Engineer",
                    company="Recent Co",
                    job_link="https://example.com/recent",
                    source="LinkedIn",
                    status="extracted",
                    posted_timestamp=datetime(2026, 10, 5, tzinfo=timezone.utc),
                    skills_extracted='["Python"]',
                    skills_processed='{"canonical_skills":["Python","SQL"]}',
                ),
                JobPosting(
                    job_id="historical",
                    title="Data Engineer",
                    company="History Co",
                    job_link="https://example.com/history",
                    source="TopJobs",
                    status="extracted",
                    posted_timestamp=datetime(2025, 6, 20, tzinfo=timezone.utc),
                    skills_extracted='["Python","Spark"]',
                ),
                JobPosting(
                    job_id="outside-window",
                    title="Old Developer",
                    company="Archive Co",
                    job_link="https://example.com/archive",
                    source="Rooster.jobs",
                    status="extracted",
                    posted_timestamp=datetime(2024, 10, 1, tzinfo=timezone.utc),
                    skills_extracted='["Legacy"]',
                ),
            ]
        )
        db.commit()

        try:
            result = JobPostingTimeSeriesAgent.get_series(
                db,
                days=730,
                interval="month",
                today=date(2026, 10, 19),
            )
            populated = [
                point for point in result["points"] if point["job_count"] > 0
            ]

            self.assertEqual(result["total_dated_jobs"], 2)
            self.assertEqual(
                result["latest_postings"][0]["job_id"],
                "recent",
            )
            self.assertEqual(
                {point["period_start"] for point in populated},
                {"2025-06-01", "2026-10-01"},
            )
            recent_skills = next(
                point["top_skills"]
                for point in populated
                if point["period_start"] == "2026-10-01"
            )
            self.assertEqual(
                {item["skill"] for item in recent_skills},
                {"Python", "SQL"},
            )
        finally:
            db.close()
            engine.dispose()


if __name__ == "__main__":
    unittest.main()
