import difflib
import hashlib
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import pandas as pd
from sqlalchemy.orm import Session

from app.models.job_posting import JobPosting, DataCollectionRun
from app.schemas.job_posting import AgentCollectionGoal

logger = logging.getLogger("emploreralk.agents.data_collection")

IT_ROLE_PATTERN = re.compile(
    r"\b(?:"
    r"information technology|information systems|computer science|software|programmer|programming|developer|development|"
    r"web|frontend|front[- ]end|backend|back[- ]end|full[- ]stack|"
    r"data scientist|data science|data engineer|data analyst|database|"
    r"machine learning|artificial intelligence|ai engineer|"
    r"cyber ?security|information security|penetration tester|"
    r"network(?:ing)?|cloud|devops|site reliability|sre|"
    r"quality assurance|software tester|qa(?: analyst| intern| tester| engineer)?|"
    r"systems? analyst|systems? administrator|system administrator|"
    r"technical support|it support|help ?desk|"
    r"erp|sap consultant|salesforce|embedded systems?|"
    r"ui/?ux|ux/?ui|user experience|user interface|"
    r"it"
    r")\b",
    re.IGNORECASE,
)


def is_it_related_job(title: str) -> bool:
    """Only collect roles whose titles clearly identify an IT/technology field."""
    return bool(title and IT_ROLE_PATTERN.search(title))


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
    source: str = "LinkedIn"  # "LinkedIn" | "TopJobs" | "Cross-Platform"
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
    cross_platform_duplicates_merged: int
    requests_made: int
    rate_limit_events: int
    status: str  # completed, partial, failed, rate_limited
    duration_seconds: float
    sources_scraped: List[str] = field(default_factory=list)
    telemetry_trace: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LinkedInConfig:
    """Configuration for LinkedIn Guest API."""
    BASE_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting"
    JOBS_PER_PAGE = 25
    MIN_DELAY = 2.0
    MAX_DELAY = 4.0
    RATE_LIMIT_COOLDOWN = 35.0


class TopJobsConfig:
    """Configuration for TopJobs.lk portal."""
    BASE_URL = "https://www.topjobs.lk"
    SEARCH_URL = "https://www.topjobs.lk/do.landing"
    VACANCY_URL = "https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp"
    ADVERT_URL = "https://www.topjobs.lk/employer/JobAdvertismentServlet"
    IT_FUNCTIONAL_AREA = "SDQ"  # Software Development / DB / QA / Web
    MIN_DELAY = 1.5
    MAX_DELAY = 3.5


class GlobalScraperConfig:
    """Common browser simulation settings."""
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
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "no-cache",
    }


class JobDeduplicationEngine:
    """
    Multi-stage semantic & fuzzy deduplication engine.
    Detects identical and similar job postings across LinkedIn, TopJobs,
    and previous database records to guarantee unique postings.
    """

    COMPANY_LEGAL_SUFFIXES = [
        r"\(pvt\)\s*ltd", r"pvt\s*ltd", r"\(private\)\s*limited", r"private\s*limited",
        r"ltd\.?", r"inc\.?", r"llc\.?", r"corp\.?", r"sri\s*lanka", r"lanka"
    ]

    TITLE_NOISE_TOKENS = [
        r"\(\d+\)", r"\(urgent\)", r"urgent", r"remote", r"hybrid", r"onsite",
        r"full\s*time", r"part\s*time", r"contract", r"immediate"
    ]

    @classmethod
    def clean_company_name(cls, company: str) -> str:
        """Strip legal entity suffixes and country markers for canonical comparison."""
        if not company:
            return ""
        c = company.lower()
        for pattern in cls.COMPANY_LEGAL_SUFFIXES:
            c = re.sub(pattern, " ", c)
        c = re.sub(r"[^\w\s]", " ", c)
        return " ".join(c.split())

    @classmethod
    def clean_job_title(cls, title: str) -> str:
        """Strip recruitment tags (e.g. '(50)', 'Remote') for canonical comparison."""
        if not title:
            return ""
        t = title.lower()
        for pattern in cls.TITLE_NOISE_TOKENS:
            t = re.sub(pattern, " ", t)
        t = re.sub(r"[^\w\s]", " ", t)
        return " ".join(t.split())

    @classmethod
    def composite_key(cls, title: str, company: str) -> str:
        """Normalized title + company fingerprint."""
        norm_t = cls.clean_job_title(title).replace(" ", "")
        norm_c = cls.clean_company_name(company).replace(" ", "")
        return f"{norm_t}::{norm_c}"

    @classmethod
    def similarity_ratio(cls, s1: str, s2: str) -> float:
        """Calculate difflib character sequence similarity ratio."""
        if not s1 or not s2:
            return 0.0
        return difflib.SequenceMatcher(None, s1, s2).ratio()

    @classmethod
    def token_jaccard(cls, s1: str, s2: str) -> float:
        """Calculate token set Jaccard similarity."""
        set1 = set(s1.split())
        set2 = set(s2.split())
        if not set1 or not set2:
            return 0.0
        return len(set1 & set2) / len(set1 | set2)

    @classmethod
    def are_jobs_similar(
        cls,
        job1_title: str,
        job1_company: str,
        job2_title: str,
        job2_company: str,
        threshold: float = 0.85
    ) -> Tuple[bool, float, str]:
        """
        Check if two job postings represent the exact same or duplicate vacancy
        across different portals using fuzzy string & token alignment.
        """
        clean_c1 = cls.clean_company_name(job1_company)
        clean_c2 = cls.clean_company_name(job2_company)
        clean_t1 = cls.clean_job_title(job1_title)
        clean_t2 = cls.clean_job_title(job2_title)

        # 1. Exact cleaned match
        if clean_c1 == clean_c2 and clean_t1 == clean_t2:
            return True, 1.0, "Exact Title & Company Match"

        # 2. Company comparison
        c_sim = max(
            cls.similarity_ratio(clean_c1, clean_c2),
            cls.token_jaccard(clean_c1, clean_c2)
        )
        if c_sim < 0.70:
            return False, c_sim, "Different Companies"

        # 3. Title comparison
        t_sim = max(
            cls.similarity_ratio(clean_t1, clean_t2),
            cls.token_jaccard(clean_t1, clean_t2)
        )

        overall_score = (0.5 * c_sim) + (0.5 * t_sim)

        if c_sim >= 0.80 and t_sim >= 0.78 and overall_score >= threshold:
            return True, overall_score, f"Fuzzy Duplicate (Company: {c_sim:.2f}, Title: {t_sim:.2f})"

        return False, overall_score, "Below Threshold"


class LinkedInCollector:
    """Specialized collector for LinkedIn Guest API postings and full descriptions."""

    def __init__(self, session: requests.Session):
        self.session = session

    def build_search_url(self, keywords: str, location: str, start: int = 0) -> str:
        params = {"keywords": keywords, "location": location, "start": start}
        return f"{LinkedInConfig.BASE_URL}?{'&'.join(f'{k}={quote(str(v))}' for k, v in params.items())}"

    def clean_job_url(self, url: str) -> str:
        if not url:
            return ""
        return url.split("?")[0].strip()

    def extract_job_id(self, card: BeautifulSoup, clean_url: str) -> str:
        urn = card.get("data-entity-urn") or card.get("data-job-id")
        if urn:
            match = re.search(r"(\d+)", urn)
            if match:
                return f"li_{match.group(1)}"
        match = re.search(r"/view/(?:.*-)?(\d+)", clean_url)
        if match:
            return f"li_{match.group(1)}"
        return f"li_hash_{hashlib.sha256(clean_url.encode('utf-8')).hexdigest()[:16]}"

    def parse_job_card(self, card: BeautifulSoup, keyword: str) -> Optional[JobData]:
        try:
            title_tag = (
                card.find("h3", class_="base-search-card__title")
                or card.find("h3", class_="base-searchcard__title")
                or card.find("h3")
            )
            title = title_tag.text.strip() if title_tag else "Unknown Title"

            comp_tag = (
                card.find("h4", class_="base-search-card__subtitle")
                or card.find("h4", class_="base-searchcard__subtitle")
                or card.find("a", class_="hidden-nested-link")
                or card.find("h4")
            )
            company = comp_tag.text.strip() if comp_tag else "Unknown Company"

            loc_tag = (
                card.find("span", class_="job-search-card__location")
                or card.find("span", class_="job-searchcard__location")
            )
            location = loc_tag.text.strip() if loc_tag else "Sri Lanka"

            link_tag = (
                card.find("a", class_="base-card__full-link")
                or card.find("a", class_="base-search-card--link")
                or card.find("a", href=re.compile(r"/jobs/view/"))
            )
            if not link_tag or not link_tag.get("href"):
                return None
            raw_url = link_tag.get("href")
            clean_url = self.clean_job_url(raw_url)
            job_id = self.extract_job_id(card, clean_url)

            date_tag = (
                card.find("time", class_="job-search-card__listdate")
                or card.find("time", class_="job-searchcard__listdate")
                or card.find("time")
            )
            posted_date_text = date_tag.text.strip() if date_tag else "Recently"
            posted_timestamp = None
            if date_tag and date_tag.get("datetime"):
                try:
                    norm = date_tag["datetime"].replace("Z", "+00:00")
                    posted_timestamp = datetime.fromisoformat(norm)
                except Exception:
                    pass

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
                quality_score=95,
                raw_metadata={"raw_url": raw_url, "portal": "LinkedIn"}
            )
        except Exception:
            return None

    def fetch_job_description(self, job_id: str, headers: Dict[str, str]) -> Optional[str]:
        """Fetch full job description text from LinkedIn guest job posting endpoint."""
        # Extract numeric id from e.g. 'li_4476810189'
        match = re.search(r"li_(\d+)", job_id)
        if not match:
            return None
        numeric_id = match.group(1)
        url = f"{LinkedInConfig.DETAIL_URL}/{numeric_id}"

        try:
            res = self.session.get(url, headers=headers, timeout=12)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                desc_tag = (
                    soup.find("div", class_="show-more-less-html__markup")
                    or soup.find("section", class_="show-more-less-html")
                    or soup.find("div", class_="description__text")
                )
                if desc_tag:
                    description = desc_tag.get_text(separator="\n", strip=True)
                    if description:
                        return description
                logger.warning("LinkedIn job description markup missing for job %s", job_id)
            else:
                logger.warning(
                    "LinkedIn job description request failed with HTTP %s for job %s",
                    res.status_code,
                    job_id,
                )
            return None
        except Exception as e:
            logger.warning("Failed to fetch LinkedIn job description for %s: %s", job_id, e)
            return None


class TopJobsCollector:
    """Specialized collector for TopJobs.lk portal postings and full descriptions."""

    def __init__(self, session: requests.Session):
        self.session = session

    def fetch_listings(self, keyword: str, headers: Dict[str, str]) -> List[Tuple[BeautifulSoup, Dict[str, str]]]:
        """
        Query TopJobs vacancy list by keyword using POST request,
        with fallback to IT functional area category.
        """
        cards: List[Tuple[BeautifulSoup, Dict[str, str]]] = []
        try:
            # 1. Search via POST with keyword
            post_data = {
                "txtKeyWord": keyword,
                "btnSearch": "Search",
                "hdnCurrentPage": "1",
            }
            res = self.session.post(
                TopJobsConfig.VACANCY_URL,
                data=post_data,
                headers=headers,
                timeout=18
            )
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                rows = [tr for tr in soup.find_all("tr") if tr.get("id", "").startswith("tr")]
                for tr in rows:
                    cards.append((tr, {"query": keyword, "type": "keyword_search"}))

            # 2. If fewer than 15 results, augment with IT functional area
            if len(cards) < 15:
                cat_url = f"{TopJobsConfig.VACANCY_URL}?FA={TopJobsConfig.IT_FUNCTIONAL_AREA}&jst=OPEN"
                res_cat = self.session.get(cat_url, headers=headers, timeout=18)
                if res_cat.status_code == 200:
                    soup_cat = BeautifulSoup(res_cat.text, "html.parser")
                    cat_rows = [tr for tr in soup_cat.find_all("tr") if tr.get("id", "").startswith("tr")]
                    for tr in cat_rows:
                        cards.append((tr, {"query": keyword, "type": "functional_area_it"}))

        except Exception as e:
            logger.error("Error querying TopJobs listings: %s", e)

        return cards

    def parse_job_row(self, row: BeautifulSoup, meta: Dict[str, str]) -> Optional[JobData]:
        """Parse TopJobs HTML table row into standardized JobData."""
        try:
            # Title inside <h2>
            h2 = row.find("h2")
            if not h2:
                return None
            title = h2.get_text(separator=" ", strip=True)

            # Company inside <h1>
            h1 = row.find("h1")
            company = h1.get_text(separator=" ", strip=True) if h1 else "Unknown Company"

            # Codes: jc (job code), ec (employer code), ac (ad code)
            onclick_str = row.get("onclick", "")
            jc, ec, ac = "", "DEFZZZ", "DEFZZZ"
            match = re.search(r"createAlert\s*\(\s*'\d+'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'", onclick_str)
            if match:
                ac, jc, ec = match.group(1), match.group(2), match.group(3)
            else:
                # Fallback to hidden spans
                jc_span = row.find("span", id=re.compile(r"hdnJC"))
                ec_span = row.find("span", id=re.compile(r"hdnEC"))
                ac_span = row.find("span", id=re.compile(r"hdnAC"))
                if jc_span:
                    jc = jc_span.text.strip()
                if ec_span:
                    ec = ec_span.text.strip()
                if ac_span:
                    ac = ac_span.text.strip()

            if not jc:
                # Fallback to row index or hash
                jc = hashlib.sha256(f"{title}_{company}".encode("utf-8")).hexdigest()[:10]

            job_id = f"tj_{jc}"
            job_link = f"{TopJobsConfig.ADVERT_URL}?ac={ac}&jc={jc}&ec={ec}"

            # Opening date in cell
            tds = row.find_all("td")
            posted_date_text = "Recently"
            posted_timestamp = None
            if len(tds) >= 5:
                date_candidate = tds[4].get_text(strip=True)
                if date_candidate:
                    posted_date_text = date_candidate
                    try:
                        # TopJobs date format e.g. "Sun Oct 11 2026"
                        dt = datetime.strptime(date_candidate, "%a %b %d %Y")
                        posted_timestamp = dt.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

            return JobData(
                title=title,
                company=company,
                location="Sri Lanka",
                job_link=job_link,
                posted_date_text=posted_date_text,
                posted_timestamp=posted_timestamp,
                job_id=job_id,
                source="TopJobs",
                search_keyword=meta.get("query", "IT"),
                quality_score=95,
                raw_metadata={
                    "jc": jc,
                    "ec": ec,
                    "ac": ac,
                    "portal": "TopJobs.lk",
                    "discovery_type": meta.get("type", "search")
                }
            )
        except Exception as e:
            logger.debug("Failed parsing TopJobs row: %s", e)
            return None

    def fetch_job_content(
        self,
        ad_url: str,
        headers: Dict[str, str]
    ) -> Tuple[Optional[str], List[str]]:
        """Fetch text and image-based advertisement content from TopJobs."""
        try:
            res = self.session.get(ad_url, headers=headers, timeout=15)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                # The advertisement body is rendered in #remark; avoid collecting site-wide chrome.
                content = soup.find(id="remark")
                if content is None:
                    logger.warning(
                        "TopJobs advertisement body #remark missing from HTTP 200 response: %s",
                        ad_url,
                    )
                    return None, []
                image_urls = []
                for image in content.find_all("img"):
                    image_src = image.get("src") or image.get("data-src")
                    if image_src and urlparse(image_src).path.lower().endswith(
                        (".jpg", ".jpeg", ".png")
                    ):
                        image_url = urljoin(TopJobsConfig.BASE_URL + "/", image_src)
                        image_host = urlparse(image_url).hostname or ""
                        if image_host == "topjobs.lk" or image_host.endswith(".topjobs.lk"):
                            image_urls.append(image_url)
                for tag in content(["script", "style", "noscript", "meta"]):
                    tag.decompose()
                text = content.get_text(separator="\n", strip=True)
                cleaned_lines = []
                for line in text.splitlines():
                    l = line.strip()
                    if l and not l.startswith("Seems you have change your Email") and l != "VACVIEW" and l != "":
                        cleaned_lines.append(l)
                description = "\n".join(cleaned_lines)
                if not description and not image_urls:
                    logger.warning("TopJobs advertisement returned no text or images: %s", ad_url)
                return description or None, image_urls
            logger.warning(
                "TopJobs advertisement request failed with HTTP %s: %s",
                res.status_code,
                ad_url,
            )
            return None, []
        except Exception as e:
            logger.warning("Failed fetching TopJobs description from %s: %s", ad_url, e)
            return None, []


class LinkedInDataCollectionAgent:
    """
    Autonomous Job Data Collection Agent for LinkedIn & TopJobs.lk.
    
    Part of the EmploreraLK Job Market Demand Forecasting Engine (Module 1).
    Key Capabilities:
      1. Dual-Platform Crawling: Autonomously collects vacancies from both LinkedIn
         and TopJobs.lk with complete job descriptions.
      2. Multi-Stage Deduplication: Detects exact ID duplicates, identical URLs,
         and fuzzy cross-platform duplicates (same position cross-posted on both portals).
      3. Self-Healing & Polite Pacing: Senses HTTP 429 rate limiting, triggers exponential
         cooldowns with jitter, and rotates browser fingerprints.
      4. Structured Dual-Sink Persistence: Neon PostgreSQL (`job_postings`, `data_collection_runs`)
         and optional CSV exports.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.session = self._setup_session()
        self.linkedin_collector = LinkedInCollector(self.session)
        self.topjobs_collector = TopJobsCollector(self.session)

        # Episodic Memory banks
        self.memory_known_ids: Set[str] = set()
        self.memory_known_urls: Set[str] = set()
        self.memory_known_jobs: List[JobData] = []
        self.memory_topjobs_missing_descriptions: Set[str] = set()
        self.telemetry_trace: List[AgentStepTelemetry] = []

        self._load_memory()

    def _setup_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1.0,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))
        session.mount("http://", HTTPAdapter(max_retries=retries))
        return session

    def _get_random_headers(self) -> Dict[str, str]:
        headers = GlobalScraperConfig.BASE_HEADERS.copy()
        headers["User-Agent"] = random.choice(GlobalScraperConfig.USER_AGENTS)
        return headers

    def _load_memory(self) -> None:
        """Preload existing job IDs and metadata from DB to guarantee absolute uniqueness."""
        if self.db:
            try:
                existing = self.db.query(
                    JobPosting.job_id,
                    JobPosting.job_link,
                    JobPosting.title,
                    JobPosting.company,
                    JobPosting.source,
                    JobPosting.description_raw,
                ).all()

                for row in existing:
                    if row[0]:
                        self.memory_known_ids.add(row[0])
                        if row[4] == "TopJobs" and not (row[5] or "").strip():
                            self.memory_topjobs_missing_descriptions.add(row[0])
                    if row[1]:
                        self.memory_known_urls.add(row[1])
                    if row[2] and row[3]:
                        # Load minimal JobData into memory bank for fuzzy cross-platform checks
                        self.memory_known_jobs.append(
                            JobData(
                                title=row[2],
                                company=row[3],
                                location="Sri Lanka",
                                job_link=row[1] or "",
                                posted_date_text="",
                                job_id=row[0],
                                source=row[4] or "Existing"
                            )
                        )
                logger.info(
                    "Agent memory initialized with %d IDs and %d existing job profiles.",
                    len(self.memory_known_ids), len(self.memory_known_jobs)
                )
            except Exception as e:
                logger.warning("Could not pre-load memory from DB: %s", e)

    def _record_telemetry(self, action: str, thought: str, observation: str, status: str = "ok") -> None:
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

    def _evaluate_and_deduplicate(
        self,
        candidate: JobData,
        similarity_threshold: float = 0.85
    ) -> Tuple[bool, str]:
        """
        Interrogate memory bank to see if candidate is a duplicate
        (exact ID, exact URL, or fuzzy cross-platform match).
        Returns: (is_duplicate, reason)
        """
        # 1. Exact ID
        if candidate.job_id and candidate.job_id in self.memory_known_ids:
            return True, f"Exact Job ID match ({candidate.job_id})"

        # 2. Exact Link
        if candidate.job_link and candidate.job_link in self.memory_known_urls:
            return True, f"Exact URL match ({candidate.job_link})"

        # 3. Fuzzy match against memory bank (Cross-Platform & Intra-Platform)
        for existing in self.memory_known_jobs:
            is_similar, score, reason = JobDeduplicationEngine.are_jobs_similar(
                candidate.title, candidate.company,
                existing.title, existing.company,
                threshold=similarity_threshold
            )
            if is_similar:
                # Same position cross-posted on both platforms
                return True, f"Cross-platform match with {existing.source} post '{existing.title}' at '{existing.company}' (Score: {score:.2f} — {reason})"

        return False, "Unique post"

    def execute_goal(
        self,
        goal: AgentCollectionGoal,
        run_id: Optional[str] = None
    ) -> AgentExecutionReport:
        """
        Autonomously orchestrate data collection from LinkedIn and TopJobs,
        fetch complete job descriptions, perform cross-platform deduplication,
        and persist unique postings.
        """
        start_time = time.time()
        if not run_id:
            run_id = f"run_{int(time.time())}_{random.randint(1000, 9999)}"

        keywords = goal.keywords.strip()
        location = goal.location.strip()
        max_jobs = goal.max_jobs
        sources = [s.strip().lower() for s in goal.sources] if goal.sources else ["linkedin", "topjobs"]

        # Track sources to scrape
        scrape_linkedin = any("linkedin" in s for s in sources)
        scrape_topjobs = any("topjobs" in s for s in sources)
        active_sources_display = []
        if scrape_linkedin:
            active_sources_display.append("LinkedIn")
        if scrape_topjobs:
            active_sources_display.append("TopJobs.lk")

        self._record_telemetry(
            action="INITIALIZE_MULTI_PLATFORM_GOAL",
            thought=f"Deploying autonomous agent across {', '.join(active_sources_display)} for query '{keywords}' in '{location}'. Target quota: {max_jobs} unique jobs.",
            observation=f"Initial memory bank loaded with {len(self.memory_known_ids)} known IDs and {len(self.memory_known_jobs)} reference profiles.",
            status="ok"
        )

        # Initialize DB Run record
        db_run: Optional[DataCollectionRun] = None
        if self.db:
            try:
                db_run = DataCollectionRun(
                    run_id=run_id,
                    source=",".join(active_sources_display),
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

        unique_collected_jobs: List[JobData] = []
        updated_existing_descriptions = False
        non_it_jobs_filtered = 0
        topjobs_descriptions_attempted: Set[str] = set()
        duplicates_skipped = 0
        cross_platform_merged = 0
        rate_limit_events = 0
        requests_made = 0

        # Quota allocation: balance between platforms
        target_per_platform = max_jobs if len(active_sources_display) <= 1 else (max_jobs // 2) + (max_jobs % 2)

        # ─── 1. TopJobs.lk Collection Cycle ──────────────────────────────────
        if scrape_topjobs and len(unique_collected_jobs) < max_jobs:
            self._record_telemetry(
                action="ACTIVATE_TOPJOBS_CRAWLER",
                thought=f"Initiating TopJobs.lk harvest for keyword '{keywords}'.",
                observation=f"Connecting to {TopJobsConfig.BASE_URL} and {TopJobsConfig.VACANCY_URL}.",
                status="in_progress"
            )

            headers = self._get_random_headers()
            raw_cards = self.topjobs_collector.fetch_listings(keywords, headers)
            requests_made += 1

            if goal.fetch_full_description and self.db:
                existing_topjobs = self.db.query(JobPosting).filter(
                    JobPosting.source == "TopJobs"
                ).all()
                pending_backfills = []
                for existing_job in existing_topjobs:
                    if not is_it_related_job(existing_job.title):
                        continue
                    metadata = existing_job.get_metadata()
                    image_urls = metadata.get("description_image_urls", [])
                    if isinstance(image_urls, str):
                        image_urls = [image_urls]
                    if (existing_job.description_raw or "").strip() or image_urls:
                        continue
                    pending_backfills.append((existing_job, metadata))

                backfilled_descriptions = 0
                for existing_job, metadata in pending_backfills:
                    if not existing_job.job_link:
                        logger.warning(
                            "Cannot backfill TopJobs description for %s: job link is empty",
                            existing_job.job_id,
                        )
                        continue
                    topjobs_descriptions_attempted.add(existing_job.job_id)
                    time.sleep(random.uniform(0.8, goal.min_delay))
                    requests_made += 1
                    desc_text, image_urls = self.topjobs_collector.fetch_job_content(
                        existing_job.job_link, headers
                    )
                    if not desc_text and not image_urls:
                        continue
                    if desc_text:
                        existing_job.description_raw = desc_text
                    if image_urls:
                        metadata["description_image_urls"] = image_urls
                        existing_job.set_metadata(metadata)
                    existing_job.quality_score = 100
                    updated_existing_descriptions = True
                    backfilled_descriptions += 1
                    self.memory_topjobs_missing_descriptions.discard(existing_job.job_id)

                self._record_telemetry(
                    action="BACKFILL_TOPJOBS_DESCRIPTIONS",
                    thought="Retrying saved IT-related TopJobs adverts that have no stored description text or image.",
                    observation=(
                        f"Fetched descriptions for {backfilled_descriptions} of "
                        f"{len(pending_backfills)} pending TopJobs postings."
                    ),
                    status="ok" if backfilled_descriptions == len(pending_backfills) else "partial"
                )

            self._record_telemetry(
                action="PROCESS_TOPJOBS_LISTINGS",
                thought=f"Received {len(raw_cards)} raw vacancy rows from TopJobs.lk. Beginning deduplication and description extraction.",
                observation=f"Parsing HTML candidate rows.",
                status="ok"
            )

            topjobs_collected_in_batch = 0
            for tr, meta in raw_cards:
                if len(unique_collected_jobs) >= max_jobs:
                    break
                if scrape_linkedin and topjobs_collected_in_batch >= target_per_platform:
                    break

                parsed_job = self.topjobs_collector.parse_job_row(tr, meta)
                if not parsed_job or not parsed_job.job_id:
                    continue
                if not is_it_related_job(parsed_job.title):
                    non_it_jobs_filtered += 1
                    continue

                # Deduplication check
                is_dup, dup_reason = self._evaluate_and_deduplicate(
                    parsed_job, similarity_threshold=goal.similarity_threshold
                )
                if is_dup:
                    duplicates_skipped += 1
                    if "Cross-platform" in dup_reason:
                        cross_platform_merged += 1
                    if (
                        goal.fetch_full_description
                        and self.db
                        and parsed_job.job_id in self.memory_topjobs_missing_descriptions
                        and parsed_job.job_id not in topjobs_descriptions_attempted
                    ):
                        topjobs_descriptions_attempted.add(parsed_job.job_id)
                        existing_job = self.db.query(JobPosting).filter(
                            JobPosting.job_id == parsed_job.job_id,
                            JobPosting.source == "TopJobs",
                        ).first()
                        if existing_job and not (existing_job.description_raw or "").strip():
                            metadata = existing_job.get_metadata()
                            if metadata.get("description_image_urls"):
                                self.memory_topjobs_missing_descriptions.discard(parsed_job.job_id)
                            else:
                                time.sleep(random.uniform(0.8, goal.min_delay))
                                requests_made += 1
                                desc_text, image_urls = self.topjobs_collector.fetch_job_content(
                                    parsed_job.job_link, headers
                                )
                                if desc_text or image_urls:
                                    if desc_text:
                                        existing_job.description_raw = desc_text
                                    if image_urls:
                                        metadata["description_image_urls"] = image_urls
                                        existing_job.set_metadata(metadata)
                                    existing_job.quality_score = 100
                                    updated_existing_descriptions = True
                                    self.memory_topjobs_missing_descriptions.discard(parsed_job.job_id)
                    logger.debug("TopJobs duplicate skipped: %s (%s)", parsed_job.title, dup_reason)
                    continue

                # Fetch full job description if requested
                if goal.fetch_full_description and parsed_job.job_link:
                    time.sleep(random.uniform(0.8, goal.min_delay))
                    requests_made += 1
                    desc_text, image_urls = self.topjobs_collector.fetch_job_content(
                        parsed_job.job_link, headers
                    )
                    if desc_text:
                        parsed_job.description_raw = desc_text
                    if image_urls:
                        parsed_job.raw_metadata["description_image_urls"] = image_urls
                    if desc_text or image_urls:
                        parsed_job.quality_score = 100

                # Register in memory and accepted list
                self.memory_known_ids.add(parsed_job.job_id)
                self.memory_known_urls.add(parsed_job.job_link)
                self.memory_known_jobs.append(parsed_job)
                unique_collected_jobs.append(parsed_job)
                topjobs_collected_in_batch += 1


            self._record_telemetry(
                action="TOPJOBS_CYCLE_COMPLETE",
                thought=f"TopJobs phase finished. Total gathered so far: {len(unique_collected_jobs)}/{max_jobs}.",
                observation=f"TopJobs unique posts stored: {sum(1 for j in unique_collected_jobs if j.source == 'TopJobs')}.",
                status="ok"
            )

        # ─── 2. LinkedIn Collection Cycle ────────────────────────────────────
        if scrape_linkedin and len(unique_collected_jobs) < max_jobs:
            self._record_telemetry(
                action="ACTIVATE_LINKEDIN_CRAWLER",
                thought=f"Initiating LinkedIn Guest API harvest for '{keywords}' in '{location}'. Remaining quota: {max_jobs - len(unique_collected_jobs)}.",
                observation=f"Connecting to {LinkedInConfig.BASE_URL}.",
                status="in_progress"
            )

            li_offset = 0
            li_consecutive_empty = 0

            while len(unique_collected_jobs) < max_jobs and li_consecutive_empty < 3:
                target_url = self.linkedin_collector.build_search_url(keywords, location, start=li_offset)
                requests_made += 1
                headers = self._get_random_headers()

                try:
                    response = self.session.get(target_url, headers=headers, timeout=15)
                except Exception as e:
                    logger.warning("LinkedIn request network error: %s", e)
                    li_consecutive_empty += 1
                    time.sleep(4.0)
                    continue

                if response.status_code == 429:
                    rate_limit_events += 1
                    cooldown = LinkedInConfig.RATE_LIMIT_COOLDOWN + random.uniform(3.0, 7.0)
                    self._record_telemetry(
                        action="HANDLE_LINKEDIN_RATE_LIMIT",
                        thought="HTTP 429 Rate Limit encountered on LinkedIn. Activating autonomous exponential backoff and session rotation.",
                        observation=f"Cooling down for {cooldown:.1f}s before resuming.",
                        status="rate_limited"
                    )
                    time.sleep(cooldown)
                    self.session = self._setup_session()
                    self.linkedin_collector.session = self.session
                    continue

                if response.status_code != 200:
                    li_consecutive_empty += 1
                    time.sleep(3.0)
                    continue

                soup = BeautifulSoup(response.text, "html.parser")
                job_cards = soup.find_all("div", class_="base-card") or soup.find_all("li")
                if not job_cards:
                    li_consecutive_empty += 1
                    li_offset += LinkedInConfig.JOBS_PER_PAGE
                    time.sleep(random.uniform(goal.min_delay, goal.max_delay))
                    continue

                li_consecutive_empty = 0
                for card in job_cards:
                    if len(unique_collected_jobs) >= max_jobs:
                        break

                    parsed_job = self.linkedin_collector.parse_job_card(card, keywords)
                    if not parsed_job or not parsed_job.job_id:
                        continue
                    if not is_it_related_job(parsed_job.title):
                        non_it_jobs_filtered += 1
                        continue

                    # Cross-platform & intra-platform deduplication
                    is_dup, dup_reason = self._evaluate_and_deduplicate(
                        parsed_job, similarity_threshold=goal.similarity_threshold
                    )
                    if is_dup:
                        duplicates_skipped += 1
                        if "Cross-platform" in dup_reason:
                            cross_platform_merged += 1
                        logger.debug("LinkedIn duplicate skipped: %s (%s)", parsed_job.title, dup_reason)
                        continue

                    # Fetch full job description from LinkedIn guest endpoint
                    if goal.fetch_full_description and parsed_job.job_id:
                        time.sleep(random.uniform(0.6, goal.min_delay))
                        requests_made += 1
                        desc_text = self.linkedin_collector.fetch_job_description(parsed_job.job_id, headers)
                        if desc_text:
                            parsed_job.description_raw = desc_text
                            parsed_job.quality_score = 100

                    # Register in memory and accepted list
                    self.memory_known_ids.add(parsed_job.job_id)
                    self.memory_known_urls.add(parsed_job.job_link)
                    self.memory_known_jobs.append(parsed_job)
                    unique_collected_jobs.append(parsed_job)

                li_offset += LinkedInConfig.JOBS_PER_PAGE
                time.sleep(random.uniform(goal.min_delay, goal.max_delay))

        # ─── 3. Database Persistence & Finalization ──────────────────────────
        saved_db_count = 0
        if self.db and (unique_collected_jobs or updated_existing_descriptions):
            try:
                for job in unique_collected_jobs:
                    # Check if already in DB (safety check)
                    existing_db = self.db.query(JobPosting.id).filter(JobPosting.job_id == job.job_id).first()
                    if existing_db:
                        continue

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
                    saved_db_count += 1

                self.db.commit()
                logger.info("Committed %d unique multi-platform job postings to database.", saved_db_count)
            except Exception as e:
                logger.error("Failed committing jobs to database: %s", e)
                if self.db:
                    self.db.rollback()

        # Optional CSV Export
        if goal.export_csv and unique_collected_jobs:
            self._export_to_csv(unique_collected_jobs, goal.csv_filename)

        duration = round(time.time() - start_time, 2)
        final_status = "completed" if len(unique_collected_jobs) >= max_jobs else "partial"
        if rate_limit_events > 0 and len(unique_collected_jobs) == 0:
            final_status = "rate_limited"

        if non_it_jobs_filtered:
            self._record_telemetry(
                action="FILTER_NON_IT_POSTINGS",
                thought="Excluded postings that are not clearly related to information technology.",
                observation=f"Filtered {non_it_jobs_filtered} non-IT postings before persistence.",
                status="ok"
            )

        report = AgentExecutionReport(
            run_id=run_id,
            goal_keywords=keywords,
            goal_location=location,
            target_count=max_jobs,
            jobs_collected=len(unique_collected_jobs),
            new_saved_count=saved_db_count if self.db else len(unique_collected_jobs),
            duplicates_skipped=duplicates_skipped,
            cross_platform_duplicates_merged=cross_platform_merged,
            requests_made=requests_made,
            rate_limit_events=rate_limit_events,
            status=final_status,
            duration_seconds=duration,
            sources_scraped=active_sources_display,
            telemetry_trace=[asdict(t) for t in self.telemetry_trace]
        )

        # Update DataCollectionRun record in DB
        if self.db and db_run:
            try:
                db_run.collected_count = len(unique_collected_jobs)
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
        if not filename:
            filename = f"emploreralk_jobs_{int(time.time())}.csv"
        try:
            records = [job.to_dict() for job in jobs]
            df = pd.DataFrame(records)
            df.to_csv(filename, index=False, encoding="utf-8")
            logger.info("Successfully exported %d unique jobs to CSV: %s", len(jobs), filename)
            return filename
        except Exception as e:
            logger.error("Failed exporting to CSV: %s", e)
            return ""
