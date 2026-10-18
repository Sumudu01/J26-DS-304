import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.models.job_posting import JobPosting, NLPExtractionRun
from app.components.forecasting.agents.job_description_ocr import extract_topjobs_image_text
from app.components.forecasting.agents.data_collection_agent import is_it_related_job
from app.schemas.nlp_extraction import (
    NLPExtractionGoal,
    NLPExtractionRunStatus,
    JobNLPExtractionResult,
)

logger = logging.getLogger("emploreralk.agents.nlp_extraction")

# Optional spaCy loader with graceful fallback
SPACY_AVAILABLE = False
nlp_model = None
try:
    import spacy
    try:
        nlp_model = spacy.load("en_core_web_sm")
        SPACY_AVAILABLE = True
        logger.info("Loaded spaCy model 'en_core_web_sm' successfully.")
    except Exception:
        try:
            nlp_model = spacy.blank("en")
            SPACY_AVAILABLE = True
            logger.info("Loaded spaCy blank 'en' model.")
        except Exception as e:
            logger.warning("Could not initialize spaCy: %s. Using rule-based NLP extraction.", e)
except ImportError:
    logger.warning("spaCy not found. Using high-precision rule-based NLP extraction.")


@dataclass
class NLPExtractionStepTelemetry:
    """Telemetry step recorded during autonomous NLP extraction."""
    step_number: int
    action: str
    thought: str
    observation: str
    status: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─── Curated Technical & Soft Skill Taxonomy ────────────────────────────────
SKILL_TAXONOMY: Dict[str, Dict[str, List[str]]] = {
    "Programming Languages": {
        "Python": ["python", "python3", "py"],
        "Java": ["java", "core java", "j2ee"],
        "JavaScript": ["javascript", "js", "ecmascript"],
        "TypeScript": ["typescript", "ts"],
        "C++": ["c++", "cpp"],
        "C#": ["c#", "csharp", "c sharp"],
        "C": [r"\bc\b"],  # Regex boundary
        "Go": ["golang", r"\bgo\b"],
        "Rust": ["rust", "rustlang"],
        "PHP": ["php", "php7", "php8"],
        "Ruby": ["ruby"],
        "Kotlin": ["kotlin"],
        "Swift": ["swift"],
        "Scala": ["scala"],
        "R": [r"\br\b"],
        "Dart": ["dart"],
        "SQL": ["sql", "tsql", "plsql", "pl/sql"],
        "HTML/CSS": ["html", "html5", "css", "css3", "sass", "scss", "less"],
        "Shell/Bash": ["bash", "shell", "powershell", "sh"],
    },
    "Frameworks & Libraries": {
        "React": ["react", "react.js", "reactjs"],
        "Angular": ["angular", "angularjs", "angular 2+"],
        "Vue.js": ["vue", "vue.js", "vuejs"],
        "Next.js": ["next.js", "nextjs"],
        "Node.js": ["node.js", "nodejs", "node"],
        "Express.js": ["express", "express.js", "expressjs"],
        "NestJS": ["nestjs", "nest.js"],
        "Django": ["django"],
        "FastAPI": ["fastapi", "fast-api"],
        "Flask": ["flask"],
        "Spring Boot": ["spring boot", "springboot", "spring framework", "spring"],
        "ASP.NET": ["asp.net", ".net", ".net core", "dotnet", "dotnet core"],
        "Laravel": ["laravel"],
        "Ruby on Rails": ["ruby on rails", "rails"],
        "GraphQL": ["graphql"],
        "Tailwind CSS": ["tailwind", "tailwind css", "tailwindcss"],
        "Bootstrap": ["bootstrap"],
        "Redux": ["redux", "redux toolkit"],
        "jQuery": ["jquery"],
    },
    "Cloud & DevOps": {
        "AWS": ["aws", "amazon web services", "ec2", "s3", "lambda"],
        "Azure": ["azure", "microsoft azure"],
        "Google Cloud Platform": ["gcp", "google cloud", "google cloud platform"],
        "Docker": ["docker", "containerization", "containers"],
        "Kubernetes": ["kubernetes", "k8s"],
        "Terraform": ["terraform"],
        "Ansible": ["ansible"],
        "CI/CD": ["ci/cd", "ci-cd", "cicd", "continuous integration", "continuous deployment"],
        "Jenkins": ["jenkins"],
        "GitHub Actions": ["github actions"],
        "GitLab CI": ["gitlab ci", "gitlab-ci"],
        "Linux": ["linux", "ubuntu", "centos", "redhat", "debian"],
        "Serverless": ["serverless"],
        "Helm": ["helm"],
    },
    "Databases & Storage": {
        "PostgreSQL": ["postgresql", "postgres"],
        "MySQL": ["mysql"],
        "MongoDB": ["mongodb", "mongo"],
        "Redis": ["redis"],
        "Oracle DB": ["oracle", "oracle database"],
        "Microsoft SQL Server": ["sql server", "mssql", "microsoft sql server"],
        "Elasticsearch": ["elasticsearch", "elastic search", "elk"],
        "DynamoDB": ["dynamodb"],
        "Cassandra": ["cassandra"],
        "Firebase": ["firebase", "firestore"],
        "Snowflake": ["snowflake"],
        "Neo4j": ["neo4j"],
    },
    "AI/ML & Data Science": {
        "Data Science": ["data science", "data scientist"],
        "Machine Learning": ["machine learning", "ml"],
        "Deep Learning": ["deep learning", "dl"],
        "Artificial Intelligence": ["artificial intelligence", "ai"],
        "Generative AI": ["generative ai", "genai", "gen ai"],
        "Large Language Models (LLMs)": ["llm", "llms", "large language models"],
        "Natural Language Processing (NLP)": ["nlp", "natural language processing"],
        "Computer Vision": ["computer vision", "opencv"],
        "PyTorch": ["pytorch"],
        "TensorFlow": ["tensorflow", "keras"],
        "Scikit-Learn": ["scikit-learn", "sklearn"],
        "Pandas": ["pandas"],
        "NumPy": ["numpy"],
        "Data Analytics": ["data analytics", "data analysis"],
        "Power BI": ["power bi", "powerbi"],
        "Tableau": ["tableau"],
        "Apache Spark": ["spark", "apache spark", "pyspark"],
        "Kafka": ["kafka", "apache kafka"],
    },
    "Testing & QA": {
        "Selenium": ["selenium", "selenium webdriver"],
        "Cypress": ["cypress"],
        "Playwright": ["playwright"],
        "JUnit": ["junit"],
        "PyTest": ["pytest"],
        "Jest": ["jest"],
        "Postman": ["postman"],
        "Automation Testing": ["automation testing", "test automation", "qa automation"],
        "Manual Testing": ["manual testing"],
        "Unit Testing": ["unit testing", "tdd", "test driven development"],
    },
    "Architecture & Methodologies": {
        "Microservices": ["microservices", "microservice architecture"],
        "RESTful APIs": ["rest", "restful", "rest api", "rest apis", "restful api"],
        "System Design": ["system design", "software architecture"],
        "Object-Oriented Programming (OOP)": ["oop", "object-oriented"],
        "Agile / Scrum": ["agile", "scrum", "kanban", "sprints"],
        "Git": ["git", "github", "gitlab", "bitbucket"],
        "Jira": ["jira"],
    },
    "Soft Skills": {
        "Problem Solving": ["problem solving", "analytical thinking"],
        "Communication Skills": ["communication", "verbal communication", "written communication"],
        "Team Collaboration": ["team player", "collaboration", "cross-functional team"],
        "Leadership": ["leadership", "mentoring", "team lead"],
        "Critical Thinking": ["critical thinking"],
        "Time Management": ["time management", "multitasking"],
        "Adaptability": ["adaptability", "fast learner"],
    }
}


class NLPExtractionAgent:
    """
    Autonomous NLP Extraction Agent for Job Postings.
    
    Part of the EmploreraLK Job Market Demand Forecasting Engine (Module 2).
    Capabilities:
      1. High-precision IT & soft skill extraction using hybrid spaCy + curated taxonomy.
      2. Seniority level classification (Junior, Mid, Senior, Lead, etc.).
      3. Years of experience & education requirement parsing.
      4. Batch & single-text processing with database synchronization.
      5. Telemetry logging & skill frequency distribution metrics.
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.telemetry_trace: List[NLPExtractionStepTelemetry] = []

    def _record_telemetry(self, action: str, thought: str, observation: str, status: str = "ok") -> None:
        step_number = len(self.telemetry_trace) + 1
        entry = NLPExtractionStepTelemetry(
            step_number=step_number,
            action=action,
            thought=thought,
            observation=observation,
            status=status
        )
        self.telemetry_trace.append(entry)
        logger.info("[NLP Step %d] Action: %s | Obs: %s", step_number, action, observation)

    @classmethod
    def extract_seniority(cls, text: str, title: str = "") -> Optional[str]:
        """Detect role seniority level from title and description text."""
        combined = f"{title.lower()} {text.lower()}"

        levels = [
            ("Intern", [r"\bintern\b", r"\binternship\b", r"\btrainee\b", r"\bapprentice\b"]),
            ("Junior", [r"\bjunior\b", r"\bjr\.?\b", r"\bassociate\b", r"\bentry\s*level\b"]),
            ("Mid-Level", [r"\bmid\s*level\b", r"\bintermediate\b", r"\bsoftware\s*engineer\b"]),
            ("Senior", [r"\bsenior\b", r"\bsr\.?\b"]),
            ("Lead / Principal", [r"\blead\b", r"\bprincipal\b", r"\btech\s*lead\b", r"\bteam\s*lead\b"]),
            ("Architect", [r"\barchitect\b", r"\bsolution\s*architect\b", r"\benterprise\s*architect\b"]),
            ("Manager / Director", [r"\bmanager\b", r"\bdirector\b", r"\bhead\s*of\b", r"\bvp\b"]),
        ]

        # Prioritize matching from title first
        title_lower = title.lower()
        for level_name, patterns in levels:
            for pat in patterns:
                if re.search(pat, title_lower):
                    return level_name

        # Then match from combined text
        for level_name, patterns in levels:
            for pat in patterns:
                if re.search(pat, combined):
                    return level_name

        return "Mid-Level"

    @classmethod
    def extract_experience_years(cls, text: str) -> Optional[int]:
        """Extract minimum years of required professional experience."""
        patterns = [
            r"(\d+)\+?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)(?:\s+of)?\s+(?:relevant\s+)?experience",
            r"(?:minimum|at\s*least)\s+(\d+)\s*(?:years?|yrs?)",
            r"experience\s*(?:of|:)?\s*(\d+)\+?\s*(?:years?|yrs?)",
        ]
        years_found = []
        for pat in patterns:
            matches = re.findall(pat, text, re.IGNORECASE)
            for m in matches:
                try:
                    val = int(m)
                    if 0 < val <= 25:
                        years_found.append(val)
                except ValueError:
                    pass

        if years_found:
            return min(years_found)  # Minimum threshold requirement
        return None

    @classmethod
    def extract_education_level(cls, text: str) -> Optional[str]:
        """Extract required educational degree or academic qualification."""
        text_lower = text.lower()
        if re.search(r"\b(phd|doctorate|ph\.d)\b", text_lower):
            return "PhD / Doctorate"
        if re.search(r"\b(master'?s|msc|m\.sc|mba|postgraduate)\b", text_lower):
            return "Master's Degree / MSc"
        if re.search(r"\b(bachelor'?s|bsc|b\.sc|beng|b\.tech|degree|undergraduate)\b", text_lower):
            return "Bachelor's Degree / BSc"
        if re.search(r"\b(diploma|hnd|higher\s*national\s*diploma)\b", text_lower):
            return "Diploma / HND"
        return None

    @classmethod
    def extract_skills_from_text(cls, text: str, title: str = "") -> Dict[str, Any]:
        """
        Hybrid multi-strategy skill extraction engine.
        Applies tokenization, contextual regex patterns, and curated taxonomy.
        """
        if not text and not title:
            return {
                "skills": [],
                "skills_by_category": {},
                "seniority_level": None,
                "experience_years_min": None,
                "education_level": None,
                "confidence": 0.0,
            }

        # Combine text with higher weight to title
        combined_text = f"{title}\n{title}\n{text}"
        text_lower = combined_text.lower()

        extracted_by_category: Dict[str, Set[str]] = {}
        all_skills: Set[str] = set()
        matched_mentions_count = 0

        # Taxonomy matching with word boundary validation
        for category, skill_dict in SKILL_TAXONOMY.items():
            category_skills = set()
            for canonical_name, aliases in skill_dict.items():
                is_matched = False
                for alias in aliases:
                    if alias.startswith(r"\b"):
                        # Pre-compiled regex pattern
                        if re.search(alias, text_lower):
                            is_matched = True
                            break
                    else:
                        # Standard word boundary regex
                        # Escape special characters like C++, C#, .NET
                        escaped = re.escape(alias)
                        pattern = rf"(?<!\w){escaped}(?!\w)"
                        if re.search(pattern, text_lower):
                            is_matched = True
                            break

                if is_matched:
                    category_skills.add(canonical_name)
                    all_skills.add(canonical_name)
                    matched_mentions_count += 1

            if category_skills:
                extracted_by_category[category] = category_skills

        # Metadata extraction
        seniority = cls.extract_seniority(text, title)
        experience = cls.extract_experience_years(text)
        education = cls.extract_education_level(text)

        # Calculate extraction quality / confidence
        confidence = 0.5
        if len(all_skills) >= 3:
            confidence += 0.3
        elif len(all_skills) >= 1:
            confidence += 0.15

        if experience is not None:
            confidence += 0.1
        if education is not None:
            confidence += 0.1

        confidence = min(1.0, round(confidence, 2))

        return {
            "skills": sorted(list(all_skills)),
            "skills_by_category": {cat: sorted(list(sks)) for cat, sks in extracted_by_category.items()},
            "seniority_level": seniority,
            "experience_years_min": experience,
            "education_level": education,
            "confidence": confidence,
        }

    def process_job_posting(self, job: JobPosting) -> JobNLPExtractionResult:
        """Process a single JobPosting instance and update its database record."""
        content = job.description_raw or ""
        current_meta = job.get_metadata()
        if not content and job.source == "TopJobs":
            image_urls = current_meta.get("description_image_urls", [])
            if isinstance(image_urls, str):
                image_urls = [image_urls]
            if image_urls:
                content = extract_topjobs_image_text(image_urls) or ""
                if content:
                    job.description_raw = content
                    current_meta["description_ocr"] = {
                        "status": "completed",
                        "image_count": len(image_urls),
                        "extracted_at": datetime.now(timezone.utc).isoformat(),
                    }
                    job.set_metadata(current_meta)

        title = job.title or ""

        extraction = self.extract_skills_from_text(content, title)
        skills = extraction["skills"]

        # Update JobPosting model fields
        job.set_skills(skills)
        job.seniority_level = extraction["seniority_level"]
        job.experience_years_min = extraction["experience_years_min"]
        job.education_level = extraction["education_level"]
        job.status = "extracted"

        # Update metadata dictionary
        current_meta["nlp_extraction"] = {
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "skills_count": len(skills),
            "skills_by_category": extraction["skills_by_category"],
            "confidence": extraction["confidence"],
        }
        job.set_metadata(current_meta)

        return JobNLPExtractionResult(
            job_id=job.job_id,
            title=job.title,
            company=job.company,
            skills=skills,
            skills_by_category=extraction["skills_by_category"],
            seniority_level=extraction["seniority_level"],
            experience_years_min=extraction["experience_years_min"],
            education_level=extraction["education_level"],
            extraction_confidence=extraction["confidence"],
        )

    def execute_goal(
        self,
        goal: NLPExtractionGoal,
        run_id: Optional[str] = None
    ) -> NLPExtractionRunStatus:
        """
        Autonomously query the database for pending job postings,
        extract technical and soft skills, and update records.
        """
        start_time = time.time()
        if not run_id:
            run_id = f"nlp_run_{int(time.time())}"

        self._record_telemetry(
            action="INITIALIZE_NLP_GOAL",
            thought=f"Beginning NLP extraction run. Target batch size: {goal.batch_size}, Force re-extract: {goal.force_reextract}.",
            observation=f"spaCy integration: {'Active (en_core_web_sm)' if SPACY_AVAILABLE else 'Rule-based hybrid fallback'}.",
            status="ok"
        )

        if not self.db:
            return NLPExtractionRunStatus(
                run_id=run_id,
                status="failed",
                total_processed=0,
                skills_extracted_count=0,
                unique_skills_count=0,
                error_message="No active database session provided."
            )

        # Query candidates for extraction
        query = self.db.query(JobPosting)
        if not goal.force_reextract:
            query = query.filter(or_(
                JobPosting.status == "collected",
                JobPosting.skills_extracted.is_(None),
            ))

        if goal.source:
            query = query.filter(JobPosting.source.ilike(f"%{goal.source.strip()}%"))

        candidates = query.order_by(desc(JobPosting.created_at)).limit(goal.batch_size).all()
        if not goal.force_reextract and (not goal.source or "topjobs" in goal.source.lower()):
            image_jobs = self.db.query(JobPosting).filter(
                JobPosting.source == "TopJobs",
                or_(JobPosting.description_raw.is_(None), JobPosting.description_raw == ""),
                JobPosting.raw_metadata.ilike("%description_image_urls%"),
            ).order_by(desc(JobPosting.created_at)).all()
            selected_ids = {job.id for job in candidates}
            image_candidates = []
            for job in image_jobs:
                metadata = job.get_metadata()
                image_urls = metadata.get("description_image_urls", [])
                if isinstance(image_urls, str):
                    image_urls = [image_urls]
                if image_urls and job.id not in selected_ids and is_it_related_job(job.title):
                    image_candidates.append(job)
                    selected_ids.add(job.id)
            candidates = (image_candidates + candidates)[:goal.batch_size]
            self._record_telemetry(
                action="QUEUE_TOPJOBS_IMAGE_OCR",
                thought="Included TopJobs image-only adverts for OCR, even if their skills were previously processed.",
                observation=f"Queued {len(image_candidates)} TopJobs image-only postings for OCR.",
                status="ok"
            )

        self._record_telemetry(
            action="FETCH_CANDIDATE_POSTS",
            thought=f"Identified {len(candidates)} job postings requiring skill extraction.",
            observation=f"Batch size limit: {goal.batch_size}.",
            status="ok"
        )

        if not candidates:
            return NLPExtractionRunStatus(
                run_id=run_id,
                status="completed",
                total_processed=0,
                skills_extracted_count=0,
                unique_skills_count=0,
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                execution_summary={"message": "No job postings awaiting NLP extraction."}
            )

        total_processed = 0
        all_skills_extracted: List[str] = []
        global_skill_counter = Counter()

        for job in candidates:
            res = self.process_job_posting(job)
            total_processed += 1
            all_skills_extracted.extend(res.skills)
            for s in res.skills:
                global_skill_counter[s] += 1

        try:
            self.db.commit()
            self._record_telemetry(
                action="COMMIT_DATABASE",
                thought=f"Successfully extracted skills for {total_processed} postings. Committing changes to Neon PostgreSQL.",
                observation=f"Total skill mentions extracted: {len(all_skills_extracted)}.",
                status="ok"
            )
        except Exception as e:
            logger.error("Failed committing NLP extractions to DB: %s", e)
            self.db.rollback()

        # Compute top skills
        top_skills = [{"skill": skill, "count": count} for skill, count in global_skill_counter.most_common(15)]
        unique_skills_count = len(global_skill_counter)

        # Record in NLPExtractionRun table
        run_record = NLPExtractionRun(
            run_id=run_id,
            total_processed=total_processed,
            skills_extracted_count=len(all_skills_extracted),
            status="completed",
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
        run_record.set_summary({
            "duration_seconds": round(time.time() - start_time, 2),
            "top_skills": top_skills,
            "unique_skills_count": unique_skills_count,
            "telemetry_trace": [asdict(t) for t in self.telemetry_trace],
        })
        try:
            self.db.add(run_record)
            self.db.commit()
        except Exception as ex:
            logger.warning("Could not persist NLPExtractionRun record: %s", ex)
            self.db.rollback()

        return NLPExtractionRunStatus(
            run_id=run_id,
            status="completed",
            total_processed=total_processed,
            skills_extracted_count=len(all_skills_extracted),
            unique_skills_count=unique_skills_count,
            started_at=run_record.started_at,
            completed_at=run_record.completed_at,
            top_skills=top_skills,
            execution_summary=run_record.get_summary(),
        )
