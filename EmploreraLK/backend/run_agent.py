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
        description="EmploreraLK Autonomous Multi-Platform (LinkedIn & TopJobs.lk) Job Data Collection Agent"
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
        "--sources",
        nargs="+",
        default=["linkedin", "topjobs"],
        help="Target portals: 'linkedin', 'topjobs', or both (default: linkedin topjobs)"
    )
    parser.add_argument(
        "--max-jobs",
        type=int,
        default=25,
        help="Maximum unique jobs to collect (default: 25)"
    )
    parser.add_argument(
        "--no-descriptions",
        action="store_true",
        default=False,
        help="Skip fetching full job description text from detail pages"
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=0.85,
        help="Fuzzy matching threshold (0.5 - 1.0) for cross-platform deduplication (default: 0.85)"
    )
    parser.add_argument(
        "--min-delay",
        type=float,
        default=1.5,
        help="Minimum polite delay between requests in seconds (default: 1.5)"
    )
    parser.add_argument(
        "--max-delay",
        type=float,
        default=3.5,
        help="Maximum polite delay between requests in seconds (default: 3.5)"
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
        help="Custom CSV export path (default: emploreralk_jobs_<timestamp>.csv)"
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        default=False,
        help="Do not persist to PostgreSQL database"
    )

    args = parser.parse_args()

    # Normalize sources
    raw_sources = args.sources
    clean_sources = []
    for s in raw_sources:
        s_lower = s.lower()
        if "top" in s_lower:
            clean_sources.append("TopJobs")
        elif "link" in s_lower:
            clean_sources.append("LinkedIn")
        elif s_lower == "all":
            clean_sources = ["LinkedIn", "TopJobs"]
            break
        else:
            clean_sources.append(s)

    goal = AgentCollectionGoal(
        sources=clean_sources,
        keywords=args.keywords,
        location=args.location,
        max_jobs=args.max_jobs,
        fetch_full_description=not args.no_descriptions,
        similarity_threshold=args.similarity_threshold,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        export_csv=args.export_csv,
        csv_filename=args.csv_filename,
        background=False,
    )

    db_session = None
    if not args.no_db:
        try:
            logger.info("Connecting to Neon PostgreSQL database...")
            Base.metadata.create_all(bind=engine)
            db_session = SessionLocal()
            logger.info("Database connection established.")
        except Exception as e:
            logger.warning("Database unavailable (%s). Falling back to standalone memory mode.", e)

    try:
        logger.info(
            "Deploying Autonomous Multi-Platform Agent for portals: %s | Query: '%s' | Target: %d unique jobs",
            ", ".join(goal.sources), goal.keywords, goal.max_jobs
        )
        agent = LinkedInDataCollectionAgent(db=db_session)
        report = agent.execute_goal(goal)

        print("\n" + "=" * 65)
        print(" AUTONOMOUS MULTI-PLATFORM AGENT EXECUTION SUMMARY ".center(65, "="))
        print("=" * 65)
        print(f"Run ID:                           {report.run_id}")
        print(f"Portals Harvested:                {', '.join(report.sources_scraped)}")
        print(f"Target Keywords:                  {report.goal_keywords}")
        print(f"Target Location:                  {report.goal_location}")
        print(f"Target Quota:                     {report.target_count}")
        print(f"Unique Jobs Collected:            {report.jobs_collected}")
        print(f"New Saved to Database:            {report.new_saved_count}")
        print(f"Exact / Intra-Portal Duplicates:  {report.duplicates_skipped}")
        print(f"Cross-Platform Duplicates Merged: {report.cross_platform_duplicates_merged}")
        print(f"Total HTTP Requests Made:         {report.requests_made}")
        print(f"Rate Limit Cooldown Events:       {report.rate_limit_events}")
        print(f"Final Status:                     {report.status}")
        print(f"Execution Duration:               {report.duration_seconds}s")
        print("=" * 65)
        print(f"Telemetry steps logged:           {len(report.telemetry_trace)}")
        print("=" * 65 + "\n")

    finally:
        if db_session:
            db_session.close()


if __name__ == "__main__":
    main()
