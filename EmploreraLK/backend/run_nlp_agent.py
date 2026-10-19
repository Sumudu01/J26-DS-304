import argparse
import json
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal, Base, engine
from app.components.forecasting.agents.nlp_extraction_agent import NLPExtractionAgent
from app.schemas.nlp_extraction import NLPExtractionGoal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("run_nlp_agent")


def main():
    parser = argparse.ArgumentParser(
        description="EmploreraLK Autonomous NLP Skill Extraction Agent"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=50,
        help="Maximum number of job postings to process from database (default: 50)"
    )
    parser.add_argument(
        "--force-reextract",
        action="store_true",
        default=False,
        help="Re-extract skills for jobs already marked as extracted"
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Filter jobs by portal: 'LinkedIn', 'TopJobs', or 'Rooster.jobs' (default: all)"
    )
    parser.add_argument(
        "--test-text",
        type=str,
        default=None,
        help="Directly test skill extraction on an arbitrary text string"
    )
    parser.add_argument(
        "--test-title",
        type=str,
        default="Software Engineer",
        help="Job title when testing with --test-text"
    )

    args = parser.parse_args()

    # Ad-hoc text extraction mode
    if args.test_text:
        print("\n" + "=" * 65)
        print(" AD-HOC NLP SKILL EXTRACTION TEST ".center(65, "="))
        print("=" * 65)
        print(f"Title: {args.test_title}")
        print(f"Input Text: {args.test_text[:100]}...\n")

        res = NLPExtractionAgent.extract_skills_from_text(text=args.test_text, title=args.test_title)
        print(f"Detected Seniority:  {res['seniority_level']}")
        print(f"Experience Required: {res['experience_years_min']} years" if res['experience_years_min'] else "Experience Required: Not specified")
        print(f"Education Required:  {res['education_level']}")
        print(f"Extraction Quality:  {res['confidence'] * 100:.0f}%\n")
        print(f"Total Unique Skills: {len(res['skills'])}")
        print("Skills by Category:")
        for cat, sks in res['skills_by_category'].items():
            print(f"  • {cat}: {', '.join(sks)}")
        print("=" * 65 + "\n")
        return

    # Database batch mode
    db_session = None
    try:
        logger.info("Connecting to Neon PostgreSQL database...")
        Base.metadata.create_all(bind=engine)
        db_session = SessionLocal()
        logger.info("Database connection established.")
    except Exception as e:
        logger.error("Could not connect to database: %s", e)
        sys.exit(1)

    try:
        goal = NLPExtractionGoal(
            batch_size=args.batch_size,
            force_reextract=args.force_reextract,
            source=args.source,
            background=False,
        )

        logger.info("Deploying NLP Extraction Agent (batch_size=%d, force=%s)...", goal.batch_size, goal.force_reextract)
        agent = NLPExtractionAgent(db=db_session)
        report = agent.execute_goal(goal)

        print("\n" + "=" * 65)
        print(" AUTONOMOUS NLP EXTRACTION AGENT SUMMARY ".center(65, "="))
        print("=" * 65)
        print(f"Run ID:                  {report.run_id}")
        print(f"Total Postings Parsed:   {report.total_processed}")
        print(f"Total Skill Mentions:    {report.skills_extracted_count}")
        print(f"Distinct Unique Skills:  {report.unique_skills_count}")
        print(f"Execution Status:        {report.status}")
        print("=" * 65)
        if report.top_skills:
            print("Top Extracted In-Demand Skills:")
            for item in report.top_skills:
                print(f"  • {item['skill']:<25} (frequency: {item['count']})")
        print("=" * 65 + "\n")

    finally:
        if db_session:
            db_session.close()


if __name__ == "__main__":
    main()
