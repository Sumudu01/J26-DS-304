import argparse
import logging
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.database import SessionLocal, Base, engine
from app.components.forecasting.agents.data_collection_agent import LinkedInDataCollectionAgent
from app.schemas.job_posting import AgentCollectionGoal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger("run_agent")


def main():
    parser = argparse.ArgumentParser(
        description="EmploreraLK Autonomous LinkedIn Job Data Collection Agent"
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="Information Technology",
        help="Search query keywords (default: 'Information Technology')"
    )
    parser.add_argument(
        "--location",
        type=str,
        default="sri lanka",
        help="Target location (default: 'sri lanka')"
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=50,
        help="Maximum jobs to collect (default: 50)"
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=2.0,
        help="Minimum polite delay between requests in seconds (default: 2.0)"
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=4.5,
        help="Maximum polite delay between requests in seconds (default: 4.5)"
    )
    parser.add_argument(
        "--export-csv",
        action="store_true",
        default=True,
        help="Export scraped jobs to CSV file (default: True)"
    )
    parser.add_argument(
        "--csv-filename",
        type=str,
        default=None,
        help="Custom CSV export path (default: linkedin_jobs_<timestamp>.csv)"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        default=False,
        help="Do not persist to PostgreSQL database"
    )

    args = parser.parse_args()

    goal = AgentCollectionGoal(
        keywords=args.keywords,
        location=args.location,
        max_jobs=args.max_jobs,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        export_csv=args.export_csv,
        csv_filename=args.csv_filename,
        background=False,
    )

    db_session = None
    if not args.no_db:
        try:
            logger.info("Initializing database connection...")
            Base.metadata.create_all(bind=engine)
            db_session = SessionLocal()
            logger.info("Database connection established.")
        except Exception as e:
            logger.warning("Could not establish database connection (%s). Operating in standalone memory mode.", e)

    try:
        logger.info(
            "Starting Autonomous Data Collection Agent for: keywords='%s', location='%s', max_jobs=%d",
            goal.keywords, goal.location, goal.max_jobs
        )
        agent = LinkedInDataCollectionAgent(db=db_session)
        report = agent.execute_goal(goal)

        print("\n" + "=" * 60)
        print(" autonomous agent execution summary ".center(60, "="))
        print("=" * 60)
        print(f"Run ID:             {report.run_id}")
        print(f"Target Keywords:    {report.goal_keywords}")
        print(f"Target Location:    {report.goal_location}")
        print(f"Target Count:       {report.target_count}")
        print(f"Jobs Collected:     {report.jobs_collected}")
        print(f"New Saved to DB:    {report.new_saved_count}")
        print(f"Duplicates Skipped: {report.duplicates_skipped}")
        print(f"Requests Made:      {report.requests_made}")
        print(f"Rate Limit Events:  {report.rate_limit_events}")
        print(f"Status:             {report.status}")
        print(f"Duration:           {report.duration_seconds}s")
        print("=" * 60)
        print(f"Telemetry steps recorded: {len(report.telemetry_trace)}")
        print("=" * 60 + "\n")

    finally:
        if db_session:
            db_session.close()


if __name__ == "__main__":
    main()
