import hashlib
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import pandas as pd
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting, DataCollectionRun
from app.schemas.job_posting import AgentCollectionGoal

logger = logging.getLogger("emploreralk.agents.data_collection")


@dataclass
class JobData:
    """Standardized representation of an autonomously extracted job posting."""
    title: str
    company: str
    location: str
    job_link: str
    posted_date_text: str
    posted_timestamp: Optional[datetime] = None
    job_id: Optional[str] = None
    source: str = "LinkedIn"
    search_keyword: Optional[str] = None
    quality_score: int = 100
    description_raw: Optional[str] = None
    raw_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.posted_timestamp:
            data["posted_timestamp"] = self.posted_timestamp.isoformat()
        return data


@dataclass
class AgentStepTelemetry:
    """Agent step-by-step reasoning and telemetry record."""
    step_number: int
    action: str
    thought: str
    observation: str
    status: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class AgentExecutionReport:
    """Comprehensive summary report generated at completion of an agent run."""
    run_id: str
    goal_keywords: str
    goal_location: str
    target_count: int
    jobs_collected: int
    new_saved_count: int
    duplicates_skipped: int
    requests_made: int
    rate_limit_events: int
    status: str  # completed, partial, failed, rate_limited
    duration_seconds: float
    telemetry_trace: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ScraperConfig:
    """Agent web communication, header rotation pool, and polite pacing configuration."""
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    JOBS_PER_PAGE = 25
    MIN_DELAY = 2.0
    MAX_DELAY = 4.5
    RATE_LIMIT_COOLDOWN = 35.0
    MAX_CONSECUTIVE_EMPTY_PAGES = 3
    MAX_RETRIES_PER_REQUEST = 3

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/123.0.0.0 Safari/537.36",
    ]

    BASE_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
    }


class LinkedInDataCollectionAgent:
    """
    Autonomous Data Collection Agent for Job Postings.
    
    Part of the EmploreraLK Job Market Demand Forecasting Engine (Module 1).
    Implements autonomous agentic capabilities:
      1. Goal Perception: Ingests search criteria and queries active database memory.
      2. Adaptive Planning: Dynamically manages pagination, pacing, and jitter.
      3. Cognition & Reflection: Diagnoses HTTP 429 rate limits, anti-bot roadblocks,
         and DOM layout shifts, autonomously pivoting retry backoffs and user agents.
      4. Quality & Deduplication Memory: Validates job card integrity and maintains
         session & database deduplication filters.
      5. Multi-sink Persistence: Commits to PostgreSQL via SQLAlchemy and exports CSV snapshots.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.session = self._setup_session()
        self.memory_known_ids: Set[str] = set()
        self.telemetry_trace: List[AgentStepTelemetry] = []
        self._load_memory()

    def _setup_session(self) -> requests.Session:
        """Initialize requests session with resilient retries."""
        session = requests.Session()
        retries = Retry(
            total=ScraperConfig.MAX_RETRIES_PER_REQUEST,
            backoff_factor=1.0,
            status_forcelist=[500, 502, 503, 504],
            raise_on_status=False
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        return session

    def _get_random_headers(self) -> Dict[str, str]:
        """Rotate User-Agent and headers dynamically to emulate real browser sessions."""
        headers = ScraperConfig.BASE_HEADERS.copy()
        headers["User-Agent"] = random.choice(ScraperConfig.USER_AGENTS)
        return headers

    def _load_memory(self) -> None:
        """Preload existing job IDs from database to prevent redundant re-fetching."""
        if self.db:
            try:
                existing = self.db.query(JobPosting.job_id).all()
                self.memory_known_ids = {row[0] for row in existing if row[0]}
                logger.info("Agent memory initialized with %d known job IDs from DB.", len(self.memory_known_ids))
            except Exception as e:
                logger.warning("Could not pre-load memory from DB: %s", e)

    def _record_telemetry(self, action: str, thought: str, observation: str, status: str = "ok") -> None:
        """Record step-by-step agent reasoning for telemetry and audit logs."""
        step_number = len(self.telemetry_trace) + 1
        entry = AgentStepTelemetry(
            step_number=step_number,
            action=action,
            thought=thought,
            observation=observation,
            status=status
        )
        self.telemetry_trace.append(entry)
        logger.info("[Agent Step %d] Action: %s | Obs: %s", step_number, action, observation)

    def _build_search_url(self, keywords: str, location: str, start: int = 0) -> str:
        """Build LinkedIn Guest Jobs API endpoint URL."""
        params = {
            "keywords": keywords,
            "location": location,
            "start": start,
        }
        return f"{ScraperConfig.BASE_URL}?{'&'.join(f'{k}={quote(str(v))}' for k, v in params.items())}"

    def _clean_job_url(self, url: str) -> str:
        """Strip tracking parameters from job URL for clean canonical storage."""
        if not url:
            return ""
        if "?" in url:
            url = url.split("?")[0]
        return url.strip()

    def _extract_job_id(self, card: BeautifulSoup, clean_url: str) -> str:
        """
        Extract unique job identifier using multiple fallback strategies:
        1. LinkedIn entity URN attribute (data-entity-urn)
        2. Numeric ID embedded in clean URL
        3. Deterministic SHA-256 hash of canonical URL
        """
        entity_urn = card.get("data-entity-urn") or card.get("data-job-id")
        if entity_urn:
            match = re.search(r"(\d+)", entity_urn)
            if match:
                return f"li_{match.group(1)}"

        # Try URL match, e.g. /jobs/view/12345678 or /jobs/view/software-engineer-12345678
        match = re.search(r"/view/(?:.*-)?(\d+)", clean_url)
        if match:
            return f"li_{match.group(1)}"

        # Fallback to deterministic hash
        return f"li_hash_{hashlib.sha256(clean_url.encode('utf-8')).hexdigest()[:16]}"

    def _extract_job_data(self, card: BeautifulSoup, keyword: str) -> Optional[JobData]:
        """
        Extract and evaluate structured job data from a LinkedIn HTML card
        using an autonomous fallback tree to handle layout shifts.
        """
        try:
            # 1. Title Extraction with fallback selectors
            title_tag = (
                card.find("h3", class_="base-search-card__title")
                or card.find("h3", class_="base-searchcard__title")
                or card.find("span", class_="sr-only")
                or card.find("h3")
            )
            title = title_tag.text.strip() if title_tag else "Unknown Title"

            # 2. Company Extraction with fallback selectors
            company_tag = (
                card.find("h4", class_="base-search-card__subtitle")
                or card.find("h4", class_="base-searchcard__subtitle")
                or card.find("a", class_="hidden-nested-link")
                or card.find("h4")
            )
            company = company_tag.text.strip() if company_tag else "Unknown Company"

            # 3. Location Extraction
            loc_tag = (
                card.find("span", class_="job-search-card__location")
                or card.find("span", class_="job-searchcard__location")
                or card.find("span", class_="main-job-card__location")
            )
            location = loc_tag.text.strip() if loc_tag else "Sri Lanka"

            # 4. Job Link Extraction
            link_tag = (
                card.find("a", class_="base-card__full-link")
                or card.find("a", class_="base-search-card--link")
                or card.find("a", href=re.compile(r"/jobs/view/"))
                or card.find("a")
            )
            if not link_tag or not link_tag.get("href"):
                return None
            raw_url = link_tag.get("href")
            clean_url = self._clean_job_url(raw_url)

            # 5. Extract Unique Job ID
            job_id = self._extract_job_id(card, clean_url)

            # 6. Posted Date & ISO Timestamp Extraction
            date_tag = (
                card.find("time", class_="job-search-card__listdate")
                or card.find("time", class_="job-searchcard__listdate")
                or card.find("time")
            )
            posted_date_text = date_tag.text.strip() if date_tag else "Recently"
            posted_timestamp: Optional[datetime] = None

            if date_tag and date_tag.get("datetime"):
                raw_dt_str = date_tag["datetime"]
                try:
                    # Normalize ISO 8601 UTC indicator 'Z' to '+00:00'
                    norm_str = raw_dt_str.replace("Z", "+00:00")
                    posted_timestamp = datetime.fromisoformat(norm_str)
                except Exception as ex:
                    logger.debug("Date parse fallback for %s: %s", raw_dt_str, ex)

            # 7. Quality Assessment
            quality_score = 100
            if title == "Unknown Title":
                quality_score -= 30
            if company == "Unknown Company":
                quality_score -= 30
            if not posted_timestamp:
                quality_score -= 10

            return JobData(
                title=title,
                company=company,
                location=location,
                job_link=clean_url,
                posted_date_text=posted_date_text,
                posted_timestamp=posted_timestamp,
                job_id=job_id,
                source="LinkedIn",
                search_keyword=keyword,
                quality_score=max(0, quality_score),
                raw_metadata={
                    "raw_url": raw_url,
                    "extracted_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        except Exception as e:
            logger.debug("Failed parsing job card: %s", e)
            return None

    def _fetch_page(self, url: str) -> Tuple[Optional[BeautifulSoup], int, str]:
        """
        Execute HTTP request with agent sensory assessment:
        Returns: (BeautifulSoup or None, status_code, message)
        """
        headers = self._get_random_headers()
        try:
            response = self.session.get(url, headers=headers, timeout=15)
            status = response.status_code

            if status == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                return soup, 200, "Success"
            elif status == 429:
                return None, 429, "Rate Limited (HTTP 429)"
            elif status in (403, 401):
                return None, status, f"Access Blocked/Forbidden (HTTP {status})"
            else:
                return None, status, f"Unexpected response status (HTTP {status})"
        except requests.RequestException as e:
            return None, 0, f"Network request exception: {str(e)}"

    def execute_goal(self, goal: AgentCollectionGoal, run_id: Optional[str] = None) -> AgentExecutionReport:
        """
        Autonomously execute the data collection goal.
        
        Orchestrates the autonomous loop:
          - Senses target and initializes execution run record.
          - Dynamically pages through results until target reached or end-of-results.
          - Autonomously recovers from rate limiting with backoff and header rotation.
          - Deduplicates and persists findings to database and optional CSV.
        """
        start_time = time.time()
        if not run_id:
            run_id = f"run_{int(time.time())}_{random.randint(1000, 9999)}"

        keywords = goal.keywords.strip()
        location = goal.location.strip()
        max_jobs = goal.max_jobs

        self._record_telemetry(
            action="INITIALIZE_GOAL",
            thought=f"Deploying autonomous agent for target: '{keywords}' in '{location}'. Target quota: {max_jobs} jobs.",
            observation=f"Initial memory contains {len(self.memory_known_ids)} known job IDs.",
            status="ok"
        )

        # Create DataCollectionRun record in DB if available
        db_run: Optional[DataCollectionRun] = None
        if self.db:
            try:
                db_run = DataCollectionRun(
                    run_id=run_id,
                    source="LinkedIn",
                    target_keywords=keywords,
                    target_location=location,
                    target_count=max_jobs,
                    collected_count=0,
                    duplicate_count=0,
                    status="running"
                )
                self.db.add(db_run)
                self.db.commit()
            except Exception as e:
                logger.error("Failed to initialize DataCollectionRun in DB: %s", e)
                if self.db:
                    self.db.rollback()

        all_collected_jobs: List[JobData] = []
        new_jobs_to_persist: List[JobData] = []
        duplicates_skipped = 0
        rate_limit_events = 0
        requests_made = 0
        consecutive_empty = 0
        offset = 0

        while len(all_collected_jobs) < max_jobs and consecutive_empty < ScraperConfig.MAX_CONSECUTIVE_EMPTY_PAGES:
            target_url = self._build_search_url(keywords, location, start=offset)
            requests_made += 1

            self._record_telemetry(
                action="FETCH_PAGE",
                thought=f"Requesting offset {offset}. Progress: {len(all_collected_jobs)}/{max_jobs} collected.",
                observation=f"Target URL: {target_url}",
                status="in_progress"
            )

            soup, status_code, message = self._fetch_page(target_url)

            # Autonomous Reflection on Response Status
            if status_code == 429:
                rate_limit_events += 1
                cooldown = ScraperConfig.RATE_LIMIT_COOLDOWN + random.uniform(2.0, 8.0)
                self._record_telemetry(
                    action="HANDLE_RATE_LIMIT",
                    thought="HTTP 429 Rate Limit sensed. Initiating autonomous exponential cooldown, jitter, and session rotation.",
                    observation=f"Cooling down for {cooldown:.1f} seconds before retrying.",
                    status="rate_limited"
                )
                time.sleep(cooldown)
                # Rotate session
                self.session = self._setup_session()
                continue

            elif status_code != 200:
                self._record_telemetry(
                    action="HANDLE_HTTP_ERROR",
                    thought=f"Received non-200 status {status_code}: {message}. Backing off.",
                    observation=f"Retrying offset {offset} after polite pause.",
                    status="warning"
                )
                consecutive_empty += 1
                time.sleep(5.0)
                continue

            # Parse DOM Cards
            job_cards = soup.find_all("div", class_="base-card") if soup else []
            if not job_cards:
                # Fallback to li elements
                job_cards = soup.find_all("li") if soup else []

            if not job_cards:
                consecutive_empty += 1
                self._record_telemetry(
                    action="EVALUATE_EMPTY_PAGE",
                    thought=f"No job cards found at offset {offset}. Consecutive empty count: {consecutive_empty}.",
                    observation="Possible end of available listings or dynamic block.",
                    status="warning"
                )
                offset += ScraperConfig.JOBS_PER_PAGE
                time.sleep(random.uniform(goal.min_delay, goal.max_delay))
                continue

            consecutive_empty = 0
            page_extracted_count = 0
            page_duplicates_count = 0

            for card in job_cards:
                job_data = self._extract_job_data(card, keywords)
                if not job_data or not job_data.job_id:
                    continue

                if job_data.job_id in self.memory_known_ids:
                    duplicates_skipped += 1
                    page_duplicates_count += 1
                    continue

                # Valid new job found
                self.memory_known_ids.add(job_data.job_id)
                all_collected_jobs.append(job_data)
                new_jobs_to_persist.append(job_data)
                page_extracted_count += 1

                if len(all_collected_jobs) >= max_jobs:
                    break

            self._record_telemetry(
                action="PROCESS_BATCH",
                thought=f"Parsed offset {offset}. New valid: {page_extracted_count}, Duplicates skipped: {page_duplicates_count}.",
                observation=f"Total gathered so far: {len(all_collected_jobs)}/{max_jobs}.",
                status="ok"
            )

            if len(all_collected_jobs) >= max_jobs:
                self._record_telemetry(
                    action="GOAL_SATISFIED",
                    thought=f"Target quota of {max_jobs} jobs satisfied.",
                    observation="Terminating pagination loop.",
                    status="ok"
                )
                break

            # Adaptive delay with random jitter for anti-bot politeness
            offset += ScraperConfig.JOBS_PER_PAGE
            delay = random.uniform(goal.min_delay, goal.max_delay)
            time.sleep(delay)

        # Database Persistence
        saved_db_count = 0
        if self.db and new_jobs_to_persist:
            try:
                for job in new_jobs_to_persist:
                    record = JobPosting(
                        job_id=job.job_id,
                        title=job.title,
                        company=job.company,
                        location=job.location,
                        job_link=job.job_link,
                        posted_date_text=job.posted_date_text,
                        posted_timestamp=job.posted_timestamp,
                        source=job.source,
                        search_keyword=job.search_keyword,
                        status="collected",
                        quality_score=job.quality_score,
                        description_raw=job.description_raw,
                    )
                    record.set_metadata(job.raw_metadata)
                    self.db.add(record)
                self.db.commit()
                saved_db_count = len(new_jobs_to_persist)
                logger.info("Committed %d new job postings to database.", saved_db_count)
            except Exception as e:
                logger.error("Failed to commit job postings to DB: %s", e)
                if self.db:
                    self.db.rollback()

        # Optional CSV Export
        if goal.export_csv and all_collected_jobs:
            self._export_to_csv(all_collected_jobs, goal.csv_filename)

        duration = round(time.time() - start_time, 2)
        final_status = "completed" if len(all_collected_jobs) >= max_jobs else "partial"
        if rate_limit_events > 0 and len(all_collected_jobs) == 0:
            final_status = "rate_limited"

        report = AgentExecutionReport(
            run_id=run_id,
            goal_keywords=keywords,
            goal_location=location,
            target_count=max_jobs,
            jobs_collected=len(all_collected_jobs),
            new_saved_count=saved_db_count if self.db else len(all_collected_jobs),
            duplicates_skipped=duplicates_skipped,
            requests_made=requests_made,
            rate_limit_events=rate_limit_events,
            status=final_status,
            duration_seconds=duration,
            telemetry_trace=[asdict(t) for t in self.telemetry_trace]
        )

        # Update DataCollectionRun record in DB
        if self.db and db_run:
            try:
                db_run.collected_count = len(all_collected_jobs)
                db_run.duplicate_count = duplicates_skipped
                db_run.status = final_status
                db_run.completed_at = datetime.now(timezone.utc)
                db_run.set_summary(report.to_dict())
                self.db.commit()
            except Exception as e:
                logger.error("Failed updating DataCollectionRun in DB: %s", e)
                if self.db:
                    self.db.rollback()

        return report

    def _export_to_csv(self, jobs: List[JobData], filename: Optional[str] = None) -> str:
        """Export collected jobs to CSV file for offline research & forecasting datasets."""
        if not filename:
            filename = f"linkedin_jobs_{int(time.time())}.csv"
        try:
            records = [job.to_dict() for job in jobs]
            df = pd.DataFrame(records)
            df.to_csv(filename, index=False, encoding="utf-8")
            logger.info("Successfully exported %d jobs to CSV: %s", len(jobs), filename)
            return filename
        except Exception as e:
            logger.error("Failed exporting to CSV: %s", e)
            return ""
