import json
import logging
import re
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.models.job_posting import JobPosting, SkillProcessingRun
from app.schemas.skill_processing import (
    NormalizedSkillItem,
    JobSkillProcessingResult,
    SkillProcessingGoal,
    SkillProcessingRunStatus,
)

logger = logging.getLogger("emploreralk.agents.skill_processing")


@dataclass
class SkillProcessingStepTelemetry:
    """Telemetry step recorded during autonomous Skill Processing Agent execution."""
    step_number: int
    action: str
    thought: str
    observation: str
    status: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─── Rich Multi-Tier IT Taxonomy & Ontological Graph ─────────────────────────

TAXONOMY_TREE: Dict[str, Dict[str, Dict[str, Any]]] = {
    "Software Engineering": {
        "Programming Languages": {
            "Python": {
                "aliases": ["python", "python3", "py", "pyhton", "pythn"],
                "implied": ["Scripting", "Software Engineering"],
                "subcategory": "General Purpose Language",
            },
            "Java": {
                "aliases": ["java", "core java", "j2ee", "j2se", "jdk"],
                "implied": ["Object-Oriented Programming (OOP)", "JVM Ecosystem", "Software Engineering"],
                "subcategory": "Enterprise Backend Language",
            },
            "JavaScript": {
                "aliases": ["javascript", "js", "ecmascript", "javacsript", "jscript", "es6", "es6+"],
                "implied": ["Web Development", "Frontend Development"],
                "subcategory": "Web Scripting Language",
            },
            "TypeScript": {
                "aliases": ["typescript", "ts", "type-script", "typscript"],
                "implied": ["JavaScript", "Web Development", "Object-Oriented Programming (OOP)"],
                "subcategory": "Typed Web Language",
            },
            "C++": {
                "aliases": ["c++", "cpp", "c/c++"],
                "implied": ["Object-Oriented Programming (OOP)", "Systems Programming"],
                "subcategory": "Compiled Systems Language",
            },
            "C#": {
                "aliases": ["c#", "csharp", "c sharp", "c#.net"],
                "implied": [".NET", "Object-Oriented Programming (OOP)", "Software Engineering"],
                "subcategory": "Enterprise Application Language",
            },
            "C": {
                "aliases": ["c", "c language"],
                "implied": ["Systems Programming", "Computer Science Fundamentals"],
                "subcategory": "Low-level Language",
            },
            "Go": {
                "aliases": ["golang", "go", "go language"],
                "implied": ["Backend Development", "Cloud-Native", "Systems Programming"],
                "subcategory": "Cloud Systems Language",
            },
            "Rust": {
                "aliases": ["rust", "rustlang"],
                "implied": ["Systems Programming", "Memory Safety"],
                "subcategory": "Modern Systems Language",
            },
            "PHP": {
                "aliases": ["php", "php7", "php8", "modern php"],
                "implied": ["Web Development", "Backend Development"],
                "subcategory": "Server-side Web Language",
            },
            "Ruby": {
                "aliases": ["ruby", "ruby-lang"],
                "implied": ["Web Development", "Scripting"],
                "subcategory": "Dynamic Web Language",
            },
            "Kotlin": {
                "aliases": ["kotlin", "kt"],
                "implied": ["Java", "JVM Ecosystem", "Mobile Development"],
                "subcategory": "Modern JVM / Android Language",
            },
            "Swift": {
                "aliases": ["swift", "swiftlang"],
                "implied": ["iOS Development", "Mobile Development"],
                "subcategory": "Apple Mobile Systems Language",
            },
            "Scala": {
                "aliases": ["scala"],
                "implied": ["Java", "JVM Ecosystem", "Functional Programming", "Big Data"],
                "subcategory": "Functional JVM Language",
            },
            "R": {
                "aliases": ["r", "r language", "r-lang"],
                "implied": ["Statistical Computing", "Data Science"],
                "subcategory": "Statistical Language",
            },
            "Dart": {
                "aliases": ["dart", "dartlang"],
                "implied": ["Flutter", "Mobile Development"],
                "subcategory": "Client-side Mobile Language",
            },
            "SQL": {
                "aliases": ["sql", "tsql", "t-sql", "plsql", "pl/sql", "ansi sql"],
                "implied": ["Relational Databases", "Data Querying"],
                "subcategory": "Database Query Language",
            },
            "HTML/CSS": {
                "aliases": ["html", "html5", "css", "css3", "sass", "scss", "less"],
                "implied": ["Frontend Development", "Web Development"],
                "subcategory": "Web Markup & Styling",
            },
            "Shell/Bash": {
                "aliases": ["bash", "shell", "shell script", "powershell", "sh", "zsh"],
                "implied": ["Linux", "Scripting", "DevOps"],
                "subcategory": "Command Line Automation",
            },
        },
        "Frontend Frameworks & UI": {
            "React": {
                "aliases": ["react", "react.js", "reactjs", "react js"],
                "implied": ["JavaScript", "Frontend Development", "Web Development"],
                "subcategory": "Frontend Component Library",
            },
            "Angular": {
                "aliases": ["angular", "angularjs", "angular 2+", "angular.js"],
                "implied": ["TypeScript", "Frontend Development", "Web Development"],
                "subcategory": "Enterprise Frontend Framework",
            },
            "Vue.js": {
                "aliases": ["vue", "vue.js", "vuejs", "vue 3"],
                "implied": ["JavaScript", "Frontend Development", "Web Development"],
                "subcategory": "Progressive Frontend Framework",
            },
            "Next.js": {
                "aliases": ["next.js", "nextjs", "next js"],
                "implied": ["React", "TypeScript", "Frontend Development", "Web Development"],
                "subcategory": "Full-Stack React Framework",
            },
            "Redux": {
                "aliases": ["redux", "redux toolkit", "rtk"],
                "implied": ["React", "JavaScript", "State Management"],
                "subcategory": "Frontend State Management",
            },
            "Tailwind CSS": {
                "aliases": ["tailwind", "tailwind css", "tailwindcss"],
                "implied": ["HTML/CSS", "Frontend Development"],
                "subcategory": "Utility CSS Framework",
            },
            "Bootstrap": {
                "aliases": ["bootstrap", "bootstrap 5"],
                "implied": ["HTML/CSS", "Frontend Development"],
                "subcategory": "Responsive UI Framework",
            },
            "jQuery": {
                "aliases": ["jquery"],
                "implied": ["JavaScript", "Web Development"],
                "subcategory": "Legacy Web Library",
            },
        },
        "Backend Frameworks": {
            "Node.js": {
                "aliases": ["node.js", "nodejs", "node js", "node"],
                "implied": ["JavaScript", "Backend Development", "Web Development"],
                "subcategory": "JavaScript Server Runtime",
            },
            "Express.js": {
                "aliases": ["express", "express.js", "expressjs"],
                "implied": ["Node.js", "JavaScript", "RESTful APIs", "Backend Development"],
                "subcategory": "Minimalist Node Framework",
            },
            "NestJS": {
                "aliases": ["nestjs", "nest.js", "nest js"],
                "implied": ["Node.js", "TypeScript", "Backend Development", "Architecture"],
                "subcategory": "Enterprise Node Framework",
            },
            "FastAPI": {
                "aliases": ["fastapi", "fast-api", "fast api"],
                "implied": ["Python", "RESTful APIs", "Backend Development"],
                "subcategory": "High-Performance Python Web API",
            },
            "Django": {
                "aliases": ["django", "django rest framework", "drf"],
                "implied": ["Python", "Backend Development", "Web Development"],
                "subcategory": "Full-Stack Python Framework",
            },
            "Flask": {
                "aliases": ["flask"],
                "implied": ["Python", "Backend Development"],
                "subcategory": "Python Microframework",
            },
            "Spring Boot": {
                "aliases": ["spring boot", "springboot", "spring-boot", "spring framework", "spring"],
                "implied": ["Java", "Backend Development", "Enterprise Architecture"],
                "subcategory": "Enterprise Java Framework",
            },
            ".NET": {
                "aliases": [".net", ".net core", "dotnet", "dotnet core", "asp.net", "asp.net core"],
                "implied": ["C#", "Backend Development", "Enterprise Architecture"],
                "subcategory": "Microsoft Application Framework",
            },
            "Laravel": {
                "aliases": ["laravel"],
                "implied": ["PHP", "Backend Development", "Web Development"],
                "subcategory": "Modern PHP Framework",
            },
            "Ruby on Rails": {
                "aliases": ["ruby on rails", "rails"],
                "implied": ["Ruby", "Backend Development", "Web Development"],
                "subcategory": "Convention-over-Configuration Web Framework",
            },
        },
        "Architecture & Methodologies": {
            "Microservices": {
                "aliases": ["microservices", "microservice", "micro-services", "micro-service architecture"],
                "implied": ["System Design", "Distributed Systems", "Software Architecture"],
                "subcategory": "Distributed Architectural Pattern",
            },
            "RESTful APIs": {
                "aliases": ["rest", "restful", "rest api", "restful apis", "rest apis", "restful web services"],
                "implied": ["Web Architecture", "API Design", "Backend Development"],
                "subcategory": "Web Service Protocol",
            },
            "GraphQL": {
                "aliases": ["graphql", "graph ql"],
                "implied": ["API Design", "Web Architecture"],
                "subcategory": "Modern Query Protocol",
            },
            "Object-Oriented Programming (OOP)": {
                "aliases": ["oop", "object-oriented", "object oriented programming", "oops"],
                "implied": ["Software Engineering", "Computer Science Fundamentals"],
                "subcategory": "Programming Paradigm",
            },
            "Design Patterns": {
                "aliases": ["design patterns", "solid principles", "solid", "gang of four"],
                "implied": ["Software Architecture", "Clean Code"],
                "subcategory": "Software Engineering Standards",
            },
            "System Design": {
                "aliases": ["system design", "distributed systems", "high availability", "scalability"],
                "implied": ["Software Architecture", "Enterprise Engineering"],
                "subcategory": "High-level Infrastructure Design",
            },
        },
    },
    "Cloud & DevOps": {
        "Cloud Infrastructure": {
            "AWS": {
                "aliases": ["aws", "amazon web services", "amazon aws", "ec2", "s3", "lambda", "ecs", "eks"],
                "implied": ["Cloud Infrastructure", "DevOps"],
                "subcategory": "Public Cloud Platform",
            },
            "Azure": {
                "aliases": ["azure", "microsoft azure", "ms azure"],
                "implied": ["Cloud Infrastructure", "DevOps"],
                "subcategory": "Public Cloud Platform",
            },
            "Google Cloud Platform": {
                "aliases": ["gcp", "google cloud", "google cloud platform", "bigquery"],
                "implied": ["Cloud Infrastructure", "DevOps"],
                "subcategory": "Public Cloud Platform",
            },
        },
        "Containerization & Orchestration": {
            "Docker": {
                "aliases": ["docker", "containerization", "containers", "dockerfile", "docker-compose", "dockr"],
                "implied": ["DevOps", "Infrastructure"],
                "subcategory": "Application Containerization",
            },
            "Kubernetes": {
                "aliases": ["kubernetes", "k8s", "kubernets", "kube", "k8"],
                "implied": ["Docker", "Container Orchestration", "DevOps", "Cloud-Native"],
                "subcategory": "Container Orchestrator",
            },
        },
        "CI/CD & Infrastructure as Code": {
            "CI/CD": {
                "aliases": ["ci/cd", "ci cd", "continuous integration", "continuous deployment", "continuous delivery"],
                "implied": ["DevOps", "Automation", "Software Quality"],
                "subcategory": "Automation Pipeline Methodology",
            },
            "Jenkins": {
                "aliases": ["jenkins"],
                "implied": ["CI/CD", "DevOps", "Automation"],
                "subcategory": "CI/CD Server",
            },
            "Git": {
                "aliases": ["git", "github", "gitlab", "bitbucket", "version control"],
                "implied": ["Source Control", "Software Engineering"],
                "subcategory": "Distributed Version Control",
            },
            "Terraform": {
                "aliases": ["terraform", "iac", "infrastructure as code"],
                "implied": ["DevOps", "Cloud Infrastructure"],
                "subcategory": "Declarative Cloud Provisioning",
            },
            "Linux": {
                "aliases": ["linux", "unix", "ubuntu", "centos", "redhat", "debian"],
                "implied": ["Operating Systems", "Systems Administration"],
                "subcategory": "Server Operating System",
            },
        },
    },
    "Data Science & AI": {
        "Machine Learning & AI": {
            "Machine Learning": {
                "aliases": ["machine learning", "ml", "supervised learning", "unsupervised learning"],
                "implied": ["Data Science", "Artificial Intelligence", "Python"],
                "subcategory": "Predictive Modeling",
            },
            "Deep Learning": {
                "aliases": ["deep learning", "neural networks", "dl", "ann", "cnn", "rnn"],
                "implied": ["Machine Learning", "Artificial Intelligence", "Python"],
                "subcategory": "Deep Neural Architectures",
            },
            "Artificial Intelligence": {
                "aliases": ["artificial intelligence", "ai", "genai", "generative ai"],
                "implied": ["Computer Science", "Advanced Analytics"],
                "subcategory": "Autonomous Cognitive Systems",
            },
            "Natural Language Processing (NLP)": {
                "aliases": ["nlp", "natural language processing", "text mining", "ner", "sentiment analysis"],
                "implied": ["Machine Learning", "Data Science", "Python"],
                "subcategory": "Linguistic Computing",
            },
            "Computer Vision": {
                "aliases": ["computer vision", "cv", "opencv", "image processing", "object detection"],
                "implied": ["Machine Learning", "Deep Learning", "Python"],
                "subcategory": "Visual Intelligence",
            },
            "PyTorch": {
                "aliases": ["pytorch", "torch"],
                "implied": ["Deep Learning", "Machine Learning", "Python"],
                "subcategory": "Tensors & Neural Framework",
            },
            "TensorFlow": {
                "aliases": ["tensorflow", "tf", "keras"],
                "implied": ["Deep Learning", "Machine Learning", "Python"],
                "subcategory": "End-to-End ML Framework",
            },
            "Scikit-learn": {
                "aliases": ["scikit-learn", "sklearn", "scikit learn"],
                "implied": ["Machine Learning", "Python"],
                "subcategory": "Classical ML Library",
            },
            "Large Language Models (LLMs)": {
                "aliases": ["llm", "llms", "large language models", "rag", "langchain", "prompt engineering"],
                "implied": ["Natural Language Processing (NLP)", "Artificial Intelligence", "Python"],
                "subcategory": "Generative Language Models",
            },
        },
        "Data Engineering & Analytics": {
            "Data Science": {
                "aliases": ["data science", "data scientist", "predictive analytics", "statistical analysis"],
                "implied": ["Data Analytics", "Python", "SQL"],
                "subcategory": "Scientific Data Exploration",
            },
            "Pandas": {
                "aliases": ["pandas", "numpy", "scipy"],
                "implied": ["Data Science", "Python"],
                "subcategory": "Data Manipulation Libraries",
            },
            "Apache Spark": {
                "aliases": ["spark", "apache spark", "pyspark"],
                "implied": ["Big Data", "Data Engineering", "Distributed Computing"],
                "subcategory": "Large-Scale Data Processing",
            },
            "Power BI / Tableau": {
                "aliases": ["power bi", "powerbi", "tableau", "data visualization", "bi tools"],
                "implied": ["Business Intelligence", "Data Analytics"],
                "subcategory": "Visual Business Analytics",
            },
        },
    },
    "Databases & Storage": {
        "Relational Databases": {
            "PostgreSQL": {
                "aliases": ["postgresql", "postgres", "psql", "postgress"],
                "implied": ["SQL", "Relational Databases", "Database Management"],
                "subcategory": "Open Source ACID RDBMS",
            },
            "MySQL": {
                "aliases": ["mysql", "mariadb"],
                "implied": ["SQL", "Relational Databases", "Database Management"],
                "subcategory": "Popular Open Source RDBMS",
            },
            "Microsoft SQL Server": {
                "aliases": ["mssql", "sql server", "ms sql server", "t-sql"],
                "implied": ["SQL", "Relational Databases", ".NET"],
                "subcategory": "Enterprise Microsoft RDBMS",
            },
            "Oracle Database": {
                "aliases": ["oracle", "oracle db", "oracle database", "pl/sql"],
                "implied": ["SQL", "Relational Databases", "Enterprise Database"],
                "subcategory": "Enterprise High-Scale RDBMS",
            },
        },
        "NoSQL & In-Memory": {
            "MongoDB": {
                "aliases": ["mongodb", "mongo", "nosql", "document database"],
                "implied": ["NoSQL Databases", "Database Management"],
                "subcategory": "Document-Store Database",
            },
            "Redis": {
                "aliases": ["redis", "in-memory database", "caching"],
                "implied": ["Caching", "Key-Value Store", "Database Management"],
                "subcategory": "High-Speed Key-Value Store",
            },
            "Elasticsearch": {
                "aliases": ["elasticsearch", "elastic search", "elk", "kibana", "lucene"],
                "implied": ["Full-Text Search", "Log Analytics"],
                "subcategory": "Distributed Search Engine",
            },
        },
    },
    "Quality Assurance & Testing": {
        "Software Testing": {
            "Selenium": {
                "aliases": ["selenium", "selenium webdriver"],
                "implied": ["Test Automation", "QA Testing"],
                "subcategory": "Web Browser Automation",
            },
            "Cypress": {
                "aliases": ["cypress", "cypress.io"],
                "implied": ["JavaScript", "Test Automation", "QA Testing"],
                "subcategory": "Next-Gen Frontend Testing",
            },
            "Playwright": {
                "aliases": ["playwright"],
                "implied": ["Test Automation", "QA Testing"],
                "subcategory": "Multi-browser Automation",
            },
            "JUnit": {
                "aliases": ["junit", "testng"],
                "implied": ["Java", "Unit Testing", "Test Automation"],
                "subcategory": "Java Unit Testing",
            },
            "PyTest": {
                "aliases": ["pytest", "py-test", "unittest"],
                "implied": ["Python", "Unit Testing", "Test Automation"],
                "subcategory": "Python Testing Framework",
            },
            "Postman": {
                "aliases": ["postman", "api testing"],
                "implied": ["RESTful APIs", "API Testing", "QA Testing"],
                "subcategory": "API Testing Suite",
            },
            "JMeter": {
                "aliases": ["jmeter", "performance testing", "load testing"],
                "implied": ["Performance Testing", "QA Testing"],
                "subcategory": "Load & Stress Testing",
            },
            "Test Automation": {
                "aliases": ["test automation", "qa automation", "automated testing", "qa"],
                "implied": ["Software Quality", "Quality Assurance"],
                "subcategory": "QA Methodology",
            },
        },
    },
    "Methodologies & Professional Skills": {
        "Methodologies & Process": {
            "Agile / Scrum": {
                "aliases": ["agile", "scrum", "kanban", "sprints", "jira", "confluence"],
                "implied": ["Project Management", "Software Development Lifecycle (SDLC)"],
                "subcategory": "Agile Delivery Framework",
            },
            "Test-Driven Development (TDD)": {
                "aliases": ["tdd", "test driven development", "bdd", "behavior driven development"],
                "implied": ["Software Engineering", "Quality Assurance"],
                "subcategory": "Code-First Testing Paradigm",
            },
        },
        "Soft Skills": {
            "Communication Skills": {
                "aliases": ["communication", "communication skills", "verbal communication", "written communication"],
                "implied": ["Professional Competence"],
                "subcategory": "Interpersonal Skills",
            },
            "Team Collaboration": {
                "aliases": ["teamwork", "team collaboration", "cross-functional", "collaborative"],
                "implied": ["Professional Competence"],
                "subcategory": "Interpersonal Skills",
            },
            "Leadership": {
                "aliases": ["leadership", "mentoring", "team lead", "technical lead", "coaching"],
                "implied": ["Professional Competence", "Management"],
                "subcategory": "Organizational Leadership",
            },
            "Problem Solving": {
                "aliases": ["problem solving", "analytical thinking", "critical thinking", "troubleshooting"],
                "implied": ["Professional Competence"],
                "subcategory": "Cognitive Aptitude",
            },
        },
    },
}


class SkillProcessingAgent:
    """
    Autonomous Skill Processing Agent for Component 1 (Job Market Demand Forecasting Engine).
    
    Automates advanced skill processing techniques:
    1. Multi-level Canonical Aliasing & Standardization
    2. Fuzzy String Matching & Typo Tolerance (Levenshtein / Token similarity)
    3. Hierarchical Domain & Category Taxonomy Classification
    4. Ontological Implication Deduction (e.g., FastAPI -> Python, REST APIs)
    5. Title-Boost & Position Importance Weighting (Core vs Secondary Skills)
    6. Skill Co-occurrence Graph & Clustering Matrix
    """

    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self.telemetry_trace: List[SkillProcessingStepTelemetry] = []
        self._build_lookup_indexes()

    def _build_lookup_indexes(self) -> None:
        """Flatten taxonomy into fast exact and alias lookup tables."""
        self.alias_to_canonical: Dict[str, str] = {}
        self.canonical_metadata: Dict[str, Dict[str, Any]] = {}
        self.all_canonical_names: List[str] = []

        for domain, categories in TAXONOMY_TREE.items():
            for category, skills in categories.items():
                for canonical, details in skills.items():
                    self.all_canonical_names.append(canonical)
                    meta = {
                        "canonical_name": canonical,
                        "domain": domain,
                        "category": category,
                        "subcategory": details.get("subcategory"),
                        "implied": details.get("implied", []),
                    }
                    self.canonical_metadata[canonical] = meta

                    # Register canonical name itself
                    clean_canon = canonical.lower().strip()
                    self.alias_to_canonical[clean_canon] = canonical

                    # Register all known aliases
                    for alias in details.get("aliases", []):
                        clean_alias = alias.lower().strip()
                        self.alias_to_canonical[clean_alias] = canonical

    def _log_step(self, action: str, thought: str, observation: str, status: str = "success") -> None:
        step_num = len(self.telemetry_trace) + 1
        record = SkillProcessingStepTelemetry(
            step_number=step_num,
            action=action,
            thought=thought,
            observation=observation,
            status=status,
        )
        self.telemetry_trace.append(record)
        logger.info(f"[Skill Step {step_num}] Action: {action} | Obs: {observation}")

    # ─── Automated Skill Processing Techniques ─────────────────────────────────

    def normalize_single_skill(
        self,
        raw_skill: str,
        fuzzy_threshold: float = 0.85
    ) -> Optional[Tuple[str, str, float]]:
        """
        Normalize a raw skill string to its canonical representation.
        Returns: (canonical_name, match_method, confidence)
        """
        if not raw_skill or not raw_skill.strip():
            return None

        clean_token = raw_skill.strip().lower()

        # 1. Exact match against canonical or known aliases (O(1))
        if clean_token in self.alias_to_canonical:
            return (self.alias_to_canonical[clean_token], "alias_mapping", 1.0)

        # 2. Case-insensitive match against canonical directly
        for canonical in self.all_canonical_names:
            if clean_token == canonical.lower():
                return (canonical, "exact_canonical", 1.0)

        # 3. Fuzzy string matching & typo tolerance (SequenceMatcher)
        best_match: Optional[str] = None
        best_ratio = 0.0

        for alias, canonical in self.alias_to_canonical.items():
            # Skip very short aliases for fuzzy matching to avoid false positives (e.g. "c", "r", "go")
            if len(alias) <= 3 and len(clean_token) <= 3:
                continue
            ratio = SequenceMatcher(None, clean_token, alias).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = canonical

        if best_match and best_ratio >= fuzzy_threshold:
            return (best_match, "fuzzy_match", round(best_ratio, 3))

        return None

    def process_skills_for_posting(
        self,
        raw_skills: List[str],
        job_title: str = "",
        job_id: str = "custom",
        company: str = "Unknown",
        fuzzy_threshold: float = 0.85,
        enable_implication: bool = True
    ) -> JobSkillProcessingResult:
        """
        Applies the full automated skill processing pipeline to a collection of skills:
        1. Normalization & Canonical deduplication
        2. Typo resolution
        3. Title importance boost & core skill flagging
        4. Ontological implication deduction
        5. Hierarchical categorization (Domain -> Category)
        """
        canonical_counter: Counter = Counter()
        match_methods: Dict[str, str] = {}
        confidences: Dict[str, float] = {}
        original_mentions: Dict[str, str] = {}

        # 1. Process raw input skills
        for raw in raw_skills:
            norm_res = self.normalize_single_skill(raw, fuzzy_threshold=fuzzy_threshold)
            if norm_res:
                canonical, method, conf = norm_res
                canonical_counter[canonical] += 1
                if canonical not in match_methods:
                    match_methods[canonical] = method
                    confidences[canonical] = conf
                    original_mentions[canonical] = raw
            else:
                # Retain raw unmapped skill as clean title case
                fallback_name = raw.strip().title()
                canonical_counter[fallback_name] += 1
                match_methods[fallback_name] = "unmapped"
                confidences[fallback_name] = 0.70
                original_mentions[fallback_name] = raw

        # 2. Title Boost & Core Skill Evaluation
        clean_title = (job_title or "").lower()
        title_tokens = set(re.findall(r"\b\w+\b", clean_title))

        core_skills: Set[str] = set()
        skill_weights: Dict[str, float] = {}

        for canonical in canonical_counter.keys():
            canon_lower = canonical.lower()
            # Title contains skill or skill name in title tokens
            in_title = (canon_lower in clean_title) or any(t == canon_lower for t in title_tokens)
            if in_title:
                skill_weights[canonical] = 2.0  # Title boost weight
                core_skills.add(canonical)
            else:
                skill_weights[canonical] = 1.0  # Standard weight

        # 3. Ontological Implication Deduction
        implied_deduced: Set[str] = set()
        if enable_implication:
            for canonical in list(canonical_counter.keys()):
                meta = self.canonical_metadata.get(canonical)
                if meta and meta.get("implied"):
                    for imp in meta["implied"]:
                        if imp not in canonical_counter:
                            implied_deduced.add(imp)

        # 4. Construct NormalizedSkillItems
        normalized_items: List[NormalizedSkillItem] = []
        skills_by_domain: Dict[str, List[str]] = defaultdict(list)
        skills_by_category: Dict[str, List[str]] = defaultdict(list)

        # Direct & Mapped skills
        for canonical, count in canonical_counter.items():
            meta = self.canonical_metadata.get(canonical, {})
            domain = meta.get("domain", "General IT")
            category = meta.get("category", "General")
            subcategory = meta.get("subcategory")
            meta_implied = meta.get("implied", [])

            is_core = canonical in core_skills
            weight = skill_weights.get(canonical, 1.0)
            method = match_methods.get(canonical, "exact_canonical")
            conf = confidences.get(canonical, 1.0)
            orig = original_mentions.get(canonical, canonical)

            item = NormalizedSkillItem(
                canonical_name=canonical,
                original_mention=orig,
                domain=domain,
                category=category,
                subcategory=subcategory,
                weight=weight,
                is_core=is_core,
                implied_skills=meta_implied,
                match_method=method,
                confidence=conf,
            )
            normalized_items.append(item)
            skills_by_domain[domain].append(canonical)
            skills_by_category[category].append(canonical)

        # Add deduced implied skills
        for imp in sorted(list(implied_deduced)):
            meta = self.canonical_metadata.get(imp, {})
            domain = meta.get("domain", "General IT")
            category = meta.get("category", "Implied Competencies")
            subcategory = meta.get("subcategory")

            item = NormalizedSkillItem(
                canonical_name=imp,
                original_mention=f"[Deducted via Ontology]",
                domain=domain,
                category=category,
                subcategory=subcategory,
                weight=0.6,  # Lower weight for implied skills
                is_core=False,
                implied_skills=[],
                match_method="ontological_implication",
                confidence=0.90,
            )
            normalized_items.append(item)
            skills_by_domain[domain].append(imp)
            skills_by_category[category].append(imp)

        all_canonical_list = sorted(list(canonical_counter.keys()))
        total_skills_count = len(normalized_items)

        return JobSkillProcessingResult(
            job_id=job_id,
            title=job_title or "Untitled",
            company=company,
            raw_skills=raw_skills,
            canonical_skills=all_canonical_list,
            normalized_skills=normalized_items,
            skills_by_domain=dict(skills_by_domain),
            skills_by_category=dict(skills_by_category),
            implied_skills=sorted(list(implied_deduced)),
            core_skills=sorted(list(core_skills)),
            total_skills_count=total_skills_count,
            processing_confidence=1.0,
        )

    # ─── Autonomous OODA Execution Loop ────────────────────────────────────────

    def execute_goal(
        self,
        goal: SkillProcessingGoal,
        run_id: Optional[str] = None
    ) -> SkillProcessingRunStatus:
        """
        Executes an autonomous batch skill processing run across database job postings.
        """
        if not run_id:
            run_id = f"skill_run_{int(time.time())}"

        start_time = datetime.now(timezone.utc)
        self.telemetry_trace = []

        # ── Step 1: INITIALIZE_GOAL ──
        self._log_step(
            action="INITIALIZE_SKILL_PROCESSING_GOAL",
            thought=f"Setting up autonomous skill normalization for batch_size={goal.batch_size}, fuzzy={goal.fuzzy_threshold}.",
            observation=f"Taxonomy contains {len(self.all_canonical_names)} canonical skills across {len(TAXONOMY_TREE)} domains.",
        )

        if not self.db:
            err_msg = "Database session is required to execute skill processing goal."
            logger.error(err_msg)
            return SkillProcessingRunStatus(
                run_id=run_id,
                status="failed",
                total_processed=0,
                skills_normalized_count=0,
                unique_canonical_skills_count=0,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
                error_message=err_msg,
            )

        # ── Step 2: FETCH_TARGET_POSTINGS ──
        query = self.db.query(JobPosting)
        if goal.source:
            query = query.filter(JobPosting.source == goal.source)

        if not goal.force_reprocess:
            # Select jobs that have extracted skills but haven't been fully processed yet
            query = query.filter(
                JobPosting.status.in_(["extracted", "collected"]),
                JobPosting.skills_extracted.isnot(None),
                JobPosting.skills_extracted != "[]"
            )

        candidates = query.order_by(desc(JobPosting.created_at)).limit(goal.batch_size).all()

        self._log_step(
            action="FETCH_CANDIDATE_POSTINGS",
            thought="Identified eligible job records containing extracted skill mentions.",
            observation=f"Fetched {len(candidates)} postings ready for automated skill normalization.",
        )

        if not candidates:
            self._log_step(
                action="TERMINATE_NO_WORK",
                thought="No unprocessed job records found in database.",
                observation="All collected jobs are already processed or no jobs with skills found.",
            )
            return SkillProcessingRunStatus(
                run_id=run_id,
                status="completed",
                total_processed=0,
                skills_normalized_count=0,
                unique_canonical_skills_count=0,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
                execution_summary={"message": "No unnormalized job postings required processing."},
            )

        # ── Step 3: AUTOMATED_SKILL_PROCESSING ──
        total_normalized = 0
        canonical_counter: Counter = Counter()
        domain_counter: Counter = Counter()
        co_occurrence_pairs: Counter = Counter()

        for idx, job in enumerate(candidates, start=1):
            raw_skills = job.get_skills()
            res = self.process_skills_for_posting(
                raw_skills=raw_skills,
                job_title=job.title,
                job_id=job.job_id,
                company=job.company,
                fuzzy_threshold=goal.fuzzy_threshold,
                enable_implication=goal.enable_implication,
            )

            # Store structured processed payload on JobPosting
            processed_dict = {
                "canonical_skills": res.canonical_skills,
                "core_skills": res.core_skills,
                "implied_skills": res.implied_skills,
                "skills_by_domain": res.skills_by_domain,
                "skills_by_category": res.skills_by_category,
                "normalized_items": [item.model_dump() for item in res.normalized_skills],
                "processed_at": datetime.now(timezone.utc).isoformat(),
            }
            job.set_processed_skills(processed_dict)
            job.status = "processed"
            job.processed_at = datetime.now(timezone.utc)

            # Aggregate stats
            for s in res.canonical_skills:
                canonical_counter[s] += 1
                total_normalized += 1

            for dom, sk_list in res.skills_by_domain.items():
                domain_counter[dom] += len(sk_list)

            # Co-occurrence pairs
            clean_canonicals = sorted(res.canonical_skills)
            for i in range(len(clean_canonicals)):
                for j in range(i + 1, len(clean_canonicals)):
                    pair = f"{clean_canonicals[i]}||{clean_canonicals[j]}"
                    co_occurrence_pairs[pair] += 1

        self._log_step(
            action="NORMALIZATION_COMPLETE",
            thought="Finished canonical deduplication, typo matching, and ontology expansion across batch.",
            observation=f"Normalized {total_normalized} total skill mentions across {len(candidates)} jobs.",
        )

        # ── Step 4: COMMIT_DATABASE ──
        try:
            self.db.commit()
            self._log_step(
                action="COMMIT_DATABASE",
                thought="Updated job_postings with skills_processed, marked status='processed'.",
                observation=f"Successfully committed changes for {len(candidates)} records.",
            )
        except Exception as e:
            self.db.rollback()
            logger.error("Failed to commit processed skills to database: %s", e)
            return SkillProcessingRunStatus(
                run_id=run_id,
                status="failed",
                total_processed=0,
                skills_normalized_count=0,
                unique_canonical_skills_count=0,
                started_at=start_time,
                completed_at=datetime.now(timezone.utc),
                error_message=f"Database commit error: {str(e)}",
            )

        # ── Step 5: RECORD_RUN_TELEMETRY ──
        completed_time = datetime.now(timezone.utc)
        top_skills = [{"skill": s, "frequency": count} for s, count in canonical_counter.most_common(15)]
        top_pairs = [{"pair": p, "count": count} for p, count in co_occurrence_pairs.most_common(10)]

        summary_payload = {
            "run_id": run_id,
            "total_processed": len(candidates),
            "skills_normalized_count": total_normalized,
            "unique_canonical_skills_count": len(canonical_counter),
            "top_canonical_skills": top_skills,
            "domain_distribution": dict(domain_counter),
            "top_co_occurring_pairs": top_pairs,
            "duration_seconds": round((completed_time - start_time).total_seconds(), 2),
            "telemetry_steps": [asdict(t) for t in self.telemetry_trace],
        }

        try:
            run_record = SkillProcessingRun(
                run_id=run_id,
                total_processed=len(candidates),
                skills_normalized_count=total_normalized,
                unique_canonical_skills_count=len(canonical_counter),
                status="completed",
                started_at=start_time,
                completed_at=completed_time,
            )
            run_record.set_summary(summary_payload)
            self.db.add(run_record)
            self.db.commit()
            logger.info("Saved SkillProcessingRun %s to database.", run_id)
        except Exception as e:
            logger.warning("Could not persist SkillProcessingRun telemetry: %s", e)

        return SkillProcessingRunStatus(
            run_id=run_id,
            status="completed",
            total_processed=len(candidates),
            skills_normalized_count=total_normalized,
            unique_canonical_skills_count=len(canonical_counter),
            started_at=start_time,
            completed_at=completed_time,
            top_canonical_skills=top_skills,
            domain_distribution=dict(domain_counter),
            execution_summary=summary_payload,
        )

    # ─── Query Helpers ─────────────────────────────────────────────────────────

    def get_co_occurring_skills(self, skill_name: str, limit: int = 15) -> List[Dict[str, Any]]:
        """Find skills that most frequently co-occur with a target skill in processed jobs."""
        if not self.db:
            return []

        # Find canonical representation first
        norm = self.normalize_single_skill(skill_name)
        target_canonical = norm[0] if norm else skill_name.strip()

        # Query all processed jobs
        jobs = self.db.query(JobPosting).filter(
            JobPosting.skills_processed.isnot(None)
        ).all()

        target_postings = 0
        co_counts: Counter = Counter()

        for j in jobs:
            data = j.get_processed_skills()
            canonical_list = data.get("canonical_skills", [])
            if target_canonical in canonical_list:
                target_postings += 1
                for other in canonical_list:
                    if other != target_canonical:
                        co_counts[other] += 1

        results = []
        for other_skill, count in co_counts.most_common(limit):
            strength = round(count / max(target_postings, 1), 3)
            results.append({
                "skill": other_skill,
                "co_occurrence_count": count,
                "strength": strength,
            })

        return results

    def get_taxonomy_tree(self) -> Dict[str, Any]:
        """Return the complete hierarchical taxonomy tree."""
        total_categories = sum(len(cats) for cats in TAXONOMY_TREE.values())
        return {
            "total_domains": len(TAXONOMY_TREE),
            "total_categories": total_categories,
            "total_canonical_skills": len(self.all_canonical_names),
            "tree": TAXONOMY_TREE,
        }
