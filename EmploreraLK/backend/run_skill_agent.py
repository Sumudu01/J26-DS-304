"""
Autonomous Skill Processing & Normalization Agent — Standalone CLI Runner
========================================================================
Executes automated skill normalization, typo tolerance, title importance weighting,
ontological implication deduction, and co-occurrence clustering.

Usage Examples:
    # 1. Process pending job postings from the database:
    python run_skill_agent.py --batch-size 25

    # 2. Force re-processing of all postings:
    python run_skill_agent.py --batch-size 50 --force-reprocess

    # 3. Filter processing to a specific platform:
    python run_skill_agent.py --source LinkedIn --batch-size 10

    # 4. Ad-hoc test of skill normalization on noisy tokens:
    python run_skill_agent.py --test-skills pyhton "react js" k8s postgress fastapi --test-title "Senior Python Developer"

    # 5. Query co-occurring skill clusters for a target skill:
    python run_skill_agent.py --query-cooccurrence Python

    # 6. Display taxonomy tree statistics:
    python run_skill_agent.py --show-taxonomy
"""

import argparse
import json
import logging
import sys

from app.core.database import SessionLocal
from app.components.forecasting.agents.skill_processing_agent import (
    SkillProcessingAgent,
    TAXONOMY_TREE,
)
from app.schemas.skill_processing import SkillProcessingGoal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("run_skill_agent")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous Skill Processing & Normalization Agent CLI Runner"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=25,
        help="Maximum number of job postings to normalize (default: 25)",
    )
    parser.add_argument(
        "--force-reprocess",
        action="store_true",
        help="Force re-processing of jobs that were already marked as processed",
    )
    parser.add_argument(
        "--source",
        type=str,
        default=None,
        help="Filter job postings by source platform ('LinkedIn', 'TopJobs')",
    )
    parser.add_argument(
        "--fuzzy-threshold",
        type=float,
        default=0.85,
        help="Fuzzy matching ratio threshold for typo tolerance (default: 0.85)",
    )
    parser.add_argument(
        "--no-implication",
        action="store_true",
        help="Disable automatic ontological implication deduction",
    )
    parser.add_argument(
        "--test-skills",
        nargs="+",
        help="Test ad-hoc skill normalization on arbitrary raw skill strings",
    )
    parser.add_argument(
        "--test-title",
        type=str,
        default="",
        help="Job title used for title importance boost testing with --test-skills",
    )
    parser.add_argument(
        "--query-cooccurrence",
        type=str,
        default=None,
        help="Query top co-occurring skills for a target skill from the database",
    )
    parser.add_argument(
        "--show-taxonomy",
        action="store_true",
        help="Display hierarchical taxonomy breakdown and statistics",
    )

    args = parser.parse_args()

    # ── Option 1: Display Taxonomy Structure ──
    if args.show_taxonomy:
        agent = SkillProcessingAgent()
        info = agent.get_taxonomy_tree()
        print("\n" + "=" * 65)
        print("========== HIERARCHICAL IT SKILL TAXONOMY SUMMARY ==========")
        print("=" * 65)
        print(f"Total Domains:          {info['total_domains']}")
        print(f"Total Categories:       {info['total_categories']}")
        print(f"Total Canonical Skills: {info['total_canonical_skills']}")
        print("-" * 65)
        for domain, cats in TAXONOMY_TREE.items():
            print(f"\n[Domain] {domain}")
            for cat, skills in cats.items():
                print(f"   [Category] {cat} ({len(skills)} skills)")
                sample_skills = list(skills.keys())[:6]
                print(f"      Skills: {', '.join(sample_skills)}...")
        print("=" * 65 + "\n")
        return

    # ── Option 2: Ad-Hoc Skill Normalization Test ──
    if args.test_skills:
        agent = SkillProcessingAgent()
        print("\n" + "=" * 65)
        print("========== AD-HOC SKILL NORMALIZATION & DEDUPLICATION ==========")
        print("=" * 65)
        print(f"Input Raw Skills:     {args.test_skills}")
        print(f"Context Title:        {args.test_title or 'None'}")
        print(f"Fuzzy Threshold:      {args.fuzzy_threshold}")
        print(f"Ontology Implication: {not args.no_implication}")
        print("-" * 65)

        res = agent.process_skills_for_posting(
            raw_skills=args.test_skills,
            job_title=args.test_title,
            fuzzy_threshold=args.fuzzy_threshold,
            enable_implication=not args.no_implication,
        )

        print("\n* Canonical Skills Extracted:")
        for s in res.canonical_skills:
            is_core = " [CORE / TITLE BOOST]" if s in res.core_skills else ""
            print(f"  - {s}{is_core}")

        if res.implied_skills:
            print("\n* Ontologically Implied Competencies:")
            for imp in res.implied_skills:
                print(f"  -> {imp}")

        print("\n* Domain Breakdown:")
        for dom, sk_list in res.skills_by_domain.items():
            print(f"  - {dom}: {', '.join(sk_list)}")

        print("\n* Detailed Item Audit:")
        for item in res.normalized_skills:
            print(f"  [{item.match_method:22}] {item.original_mention:20} -> {item.canonical_name:20} (Weight: {item.weight}, Conf: {item.confidence})")
        print("=" * 65 + "\n")
        return

    # ── Option 3: Query Co-occurrence Network ──
    if args.query_cooccurrence:
        logger.info("Connecting to Neon PostgreSQL database...")
        db = SessionLocal()
        try:
            agent = SkillProcessingAgent(db=db)
            co_list = agent.get_co_occurring_skills(skill_name=args.query_cooccurrence, limit=15)
            print("\n" + "=" * 65)
            print(f"======= SKILL CO-OCCURRENCE NETWORK: '{args.query_cooccurrence}' =======")
            print("=" * 65)
            if not co_list:
                print(f"No co-occurring skill relationships recorded for '{args.query_cooccurrence}'.")
            else:
                for idx, item in enumerate(co_list, 1):
                    bar = "#" * int(item["strength"] * 20)
                    print(f"  {idx:2d}. {item['skill']:25} | Mentions: {item['co_occurrence_count']:3d} | Strength: {item['strength']:.2f} {bar}")
            print("=" * 65 + "\n")
        finally:
            db.close()
        return

    # ── Option 4: Deploy Autonomous Agent over Database Records ──
    logger.info("Connecting to Neon PostgreSQL database...")
    db = SessionLocal()
    try:
        goal = SkillProcessingGoal(
            batch_size=args.batch_size,
            force_reprocess=args.force_reprocess,
            source=args.source,
            fuzzy_threshold=args.fuzzy_threshold,
            enable_implication=not args.no_implication,
            background=False,
        )

        logger.info(
            "Deploying Skill Processing Agent (batch_size=%d, force=%s, source=%s)...",
            goal.batch_size,
            goal.force_reprocess,
            goal.source or "ALL",
        )

        agent = SkillProcessingAgent(db=db)
        report = agent.execute_goal(goal)

        print("\n" + "=" * 65)
        print("============ SKILL PROCESSING AGENT EXECUTION SUMMARY ============")
        print("=" * 65)
        print(f"Run ID:                      {report.run_id}")
        print(f"Total Postings Processed:    {report.total_processed}")
        print(f"Skills Normalized Count:     {report.skills_normalized_count}")
        print(f"Unique Canonical Skills:     {report.unique_canonical_skills_count}")
        print(f"Execution Status:            {report.status}")
        print("=" * 65)

        if report.top_canonical_skills:
            print("Top Normalized Canonical Skills in Batch:")
            for item in report.top_canonical_skills:
                print(f"  * {item['skill']:28} (frequency: {item['frequency']})")

        if report.domain_distribution:
            print("\nDomain Distribution:")
            for dom, count in report.domain_distribution.items():
                print(f"  - {dom:30} : {count}")
        print("=" * 65 + "\n")

    except Exception as exc:
        logger.error("Failed to run Skill Processing Agent: %s", exc)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
