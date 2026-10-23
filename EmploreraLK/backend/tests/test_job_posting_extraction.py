import unittest
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.components.forecasting.agents.data_collection_agent import (
    JobData,
    LinkedInDataCollectionAgent,
    RoosterJobsCollector,
)
from app.components.forecasting.services.scraping_service import ScrapingService
from app.models.job_posting import JobPosting
from app.schemas.job_posting import JobPostingResponse


class JobPostingExtractionTests(unittest.TestCase):
    def test_collected_topjobs_image_description_and_skills_are_persisted(self):
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        db = test_session()
        job = JobPosting(
            job_id="topjobs-python-developer",
            title="Python Developer",
            company="Example Co",
            job_link="https://www.topjobs.lk/job/123",
            source="TopJobs",
            status="collected",
            description_raw="Hiring an experienced developer.",
        )
        job.set_metadata({"description_image_urls": ["https://www.topjobs.lk/ad.png"]})
        db.add(job)
        db.commit()

        try:
            with patch(
                "app.components.forecasting.agents.nlp_extraction_agent.extract_topjobs_image_text",
                return_value="Seeking a Python developer with strong SQL skills.",
            ) as extract_image_text:
                processed_count = ScrapingService._extract_collected_jobs(
                    db, ["topjobs-python-developer"]
                )
            persisted = db.query(JobPosting).filter_by(
                job_id="topjobs-python-developer"
            ).one()

            self.assertEqual(processed_count, 1)
            self.assertEqual(
                persisted.description_raw,
                "Hiring an experienced developer.\n\n"
                "Seeking a Python developer with strong SQL skills.",
            )
            self.assertEqual(persisted.get_skills(), ["Python", "SQL"])
            self.assertEqual(persisted.status, "extracted")
            self.assertEqual(
                ScrapingService._extract_collected_jobs(
                    db, ["topjobs-python-developer"]
                ),
                1,
            )
            extract_image_text.assert_called_once()
            extract_image_text.assert_called_once_with(
                ["https://www.topjobs.lk/ad.png"]
            )

            agent = LinkedInDataCollectionAgent(db=db)
            rooster_duplicate = JobData(
                title="Python Developer",
                company="Example Co",
                location="Colombo",
                job_link="https://rooster.jobs/jobs/123",
                posted_date_text="Recently",
                job_id="rooster_123",
                source="Rooster.jobs",
                description_raw="Python and SQL development.",
            )
            is_duplicate, reason = agent._evaluate_and_deduplicate(rooster_duplicate)
            self.assertTrue(is_duplicate)
            self.assertIn("match", reason)
            self.assertTrue(agent.updated_existing_records)
            db.commit()
            merged_response = JobPostingResponse.model_validate(persisted)
            self.assertEqual(
                merged_response.source_platforms,
                ["TopJobs", "Rooster.jobs"],
            )
            self.assertEqual(
                {source_job["source"] for source_job in merged_response.source_jobs},
                {"TopJobs", "Rooster.jobs"},
            )
            reloaded_agent = LinkedInDataCollectionAgent(db=db)
            reloaded_duplicate, reloaded_reason = reloaded_agent._find_duplicate_job(
                rooster_duplicate,
                similarity_threshold=0.85,
            )
            self.assertIsNotNone(reloaded_duplicate)
            self.assertIn("Exact Job ID match", reloaded_reason)

            response = JobPostingResponse.model_validate(persisted)
            self.assertEqual(response.description_raw, persisted.description_raw)
            self.assertEqual(response.skills_extracted, ["Python", "SQL"])

            recommended = ScrapingService.get_recommended_jobs(
                db,
                keyword="Python Developer",
                user_skills=["Python"],
            )
            self.assertEqual(
                recommended["items"][0]["description_text"],
                persisted.description_raw,
            )
            self.assertEqual(
                recommended["items"][0]["skills_extracted"],
                ["Python", "SQL"],
            )
            rooster_filtered = ScrapingService.get_recommended_jobs(
                db,
                keyword="Python Developer",
                user_skills=["Python"],
                source_filter="Rooster.jobs",
            )
            self.assertEqual(rooster_filtered["total_matched"], 1)
            self.assertEqual(
                rooster_filtered["items"][0]["source_platforms"],
                ["TopJobs", "Rooster.jobs"],
            )
            self.assertEqual(
                {source_job["source"] for source_job in rooster_filtered["items"][0]["source_jobs"]},
                {"TopJobs", "Rooster.jobs"},
            )
        finally:
            db.close()
            engine.dispose()


class RoosterJobsCollectorTests(unittest.TestCase):
    def test_searches_sri_lanka_and_parses_text_descriptions(self):
        session = Mock()
        response = Mock()
        response.json.return_value = {
            "body": {
                "data": [
                    {
                        "id": 519373,
                        "title": "Software Engineer",
                        "company_name": "Planlogic",
                        "location": "Colombo, Sri Lanka",
                        "description": "**Who we are**\n\n- Build software.",
                        "created_at": "2026-08-24 05:44:17",
                        "tags": ["Python"],
                    }
                ]
            }
        }
        session.post.return_value = response
        collector = RoosterJobsCollector(session)

        listings = collector.fetch_listings(
            "Software Engineer",
            {"User-Agent": "test"},
            max_jobs=20,
            location="Colombo",
        )
        job = collector.parse_job(listings[0], "Software Engineer")

        session.post.assert_called_once_with(
            "https://api.rooster.jobs/jobSearch/jobs/search",
            json={
                "query": ["Software Engineer"],
                "limit": 20,
                "page": 1,
                "filters": {"country": "Sri Lanka"},
            },
            headers={"User-Agent": "test"},
            timeout=20,
        )
        self.assertIsNotNone(job)
        self.assertEqual(job.job_id, "rooster_519373")
        self.assertEqual(job.source, "Rooster.jobs")
        self.assertEqual(job.job_link, "https://rooster.jobs/jobs/519373")
        self.assertEqual(job.description_raw, "Who we are\n- Build software.")


if __name__ == "__main__":
    unittest.main()
