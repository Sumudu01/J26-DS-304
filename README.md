# EmploreraLK

### AI-Based Skill Analysis and Skill Matching Recruitment System

A comprehensive AI-driven recruitment intelligence platform for Sri Lanka's IT sector, integrating longitudinal skill demand forecasting, hidden skill gap discovery, career path optimization, and semantic job-candidate matching.

---

## 📋 Project Overview

- **Project Name:** EmploreraLK
- **Project Code:** J26-DS-304
- **Academic Year:** 2026 — Final Year Research Project
- **Course:** B.Sc. (Hons) in Information Technology specialized in Data Science
- **Institution:** Sri Lanka Institute of Information Technology (SLIIT)

This platform provides an end-to-end ecosystem for predicting future IT skill demand, discovering hidden skill gaps from resumes and curriculum data, generating personalized career development roadmaps, and performing multi-stage semantic alignment between job seekers and vacancies using Agentic AI, Large Language Models, and Explainable Machine Learning.

---

## 👥 Research Team & Individual Components

| Student ID | Student Name | Role / Research Component | Primary Focus Areas |
|:---|:---|:---|:---|
| **IT23187382** | Wijeratne U.G.S.L. | **Component 1:** Job Market Demand Forecasting Engine | Autonomous Data Collection Agent, Time-Series Forecasting (ARIMA, Prophet, N-BEATS, TFT), SHAP Explainability |
| **IT23374324** | Mathumitha E. | **Component 2:** Hidden Skill Gap Discovery Engine | Knowledge Graphs (Neo4j), Multi-layer Graph Reasoning, Implicit Competency Mining |
| **IT23218994** | Athuraliya D.S. | **Component 3:** Career Path Planning and Optimization Engine | Reinforcement Learning / Path Optimization, Dynamic Career Milestones, Salary Progression |
| **IT23151406** | Sandanayaka S.D.P.D. | **Component 4:** Skill Matching and Job Alignment Engine | BGE-M3 Dense Embeddings, FAISS Vector Search, Cross-Encoder Re-ranking |

---

## 👨‍🏫 Supervisors

| Role | Name | Affiliation |
|:---|:---|:---|
| **Supervisor** | Prof. Samantha Thelijjagoda | Sri Lanka Institute of Information Technology |
| **Co-Supervisor** | Mr. Samadhi Rathnayake | Sri Lanka Institute of Information Technology |
| **External Supervisor** | Prof. Nishantha Giguruwa | Industry / Academic Expert |

---

## 📁 Repository Directory Structure

```
J26-DS-304/
├── README.md                                # Unified Project Documentation
└── EmploreraLK/
    ├── backend/                             # Python FastAPI Layered Backend
    │   ├── app/
    │   │   ├── api/                         # FastAPI Routers & Endpoints
    │   │   │   ├── deps.py                  # Authentication & DB session dependencies
    │   │   │   └── v1/
    │   │   │       ├── auth.py              # JWT Sign up, Login & OAuth2 (Google/LinkedIn)
    │   │   │       ├── profile.py           # Seeker & Recruiter profile endpoints
    │   │   │       ├── forecast.py          # Data Collection, NLP Extraction, Skill Processing & Forecasting routes
    │   │   │       ├── career_path.py       # Career pathway endpoints
    │   │   │       ├── skill_gap.py         # Skill gap discovery endpoints
    │   │   │       └── matching.py          # Candidate-to-job matching endpoints
    │   │   ├── components/                  # Domain Business Logic & AI Agents
    │   │   │   ├── forecasting/             # Component 1: Forecasting & Scraping
    │   │   │   │   ├── agents/
    │   │   │   │   │   ├── data_collection_agent.py   # Autonomous Multi-Platform Data Collection Agent
    │   │   │   │   │   ├── nlp_extraction_agent.py    # Autonomous NLP Skill & Metadata Extraction Agent
    │   │   │   │   │   ├── skill_processing_agent.py  # Autonomous Skill Processing & Normalization Agent
    │   │   │   │   │   └── insight_generation_agent.py # Forecast Explainer
    │   │   │   │   ├── services/
    │   │   │   │   │   ├── scraping_service.py        # Background collection manager
    │   │   │   │   │   ├── nlp_service.py             # NLP extraction orchestration & telemetry
    │   │   │   │   │   ├── skill_processing_service.py # Skill normalization, ontology & co-occurrence service
    │   │   │   │   │   └── forecasting_service.py     # Time-series model inference service
    │   │   │   │   └── models/
    │   │   │   │       ├── arima_model.py
    │   │   │   │       ├── prophet_model.py
    │   │   │   │       ├── nbeats_model.py
    │   │   │   │       └── tft_model.py
    │   │   │   ├── skill_gap/               # Component 2: Neo4j Graph & Gap Analyzer
    │   │   │   ├── career_path/             # Component 3: Pathway Optimizer
    │   │   │   └── matching/                # Component 4: Semantic Matcher & FAISS
    │   │   ├── core/                        # Configuration & Database Connectors
    │   │   │   ├── config.py                # Pydantic Settings & Environment variables
    │   │   │   ├── database.py              # Neon PostgreSQL engine & SessionLocal
    │   │   │   └── security.py              # JWT tokens & Passlib password hashing
    │   │   ├── models/                      # SQLAlchemy Database Entities
    │   │   │   ├── user.py                  # User authentication & profile table
    │   │   │   └── job_posting.py           # Job postings, Collection, NLP & Skill processing runs tables
    │   │   ├── schemas/                     # Pydantic Validation Schemas
    │   │   │   ├── auth.py                  # Auth request & response schemas
    │   │   │   ├── job_posting.py           # Job posting & Agent goal/telemetry schemas
    │   │   │   ├── nlp_extraction.py        # NLP Goal, Run Status & Skill Item schemas
    │   │   │   └── skill_processing.py      # Normalization, Ontology & Co-occurrence schemas
    │   │   ├── utils/                       # Common utilities & helpers
    │   │   └── main.py                      # FastAPI application entrypoint & lifespan
    │   ├── run_agent.py                     # Standalone CLI runner for Data Collection Agent
    │   ├── run_nlp_agent.py                 # Standalone CLI runner for NLP Extraction Agent
    │   ├── run_skill_agent.py               # Standalone CLI runner for Skill Processing Agent
    │   ├── requirements.txt                 # Backend Python dependencies
    │   └── .env.example                     # Environment variables template
    ├── frontend/                            # React 18 + Vite + TypeScript Frontend
    │   ├── src/
    │   │   ├── components/                  # Reusable UI elements & widgets
    │   │   ├── pages/                       # Dashboard, Forecast, SkillGap, CareerPath, Matching
    │   │   ├── context/                     # Auth & Theme state providers
    │   │   └── services/                    # Axios API client integrations
    │   ├── package.json
    │   └── vite.config.ts
    ├── docs/                                # Technical specifications & API contracts
    └── scripts/                             # Utility & deployment automation scripts
```

---

## 🛠 Technology Stack

### Backend
- **Framework:** FastAPI 0.115+ (Asynchronous, high-performance web framework)
- **Language:** Python 3.11+ / 3.13+
- **Database:** Serverless PostgreSQL 15 via [Neon Tech](https://neon.tech)
- **ORM:** SQLAlchemy 2.0+ (Declarative mapping with connection pooling & auto reconnect)
- **Data Validation:** Pydantic 2.7+ & Pydantic-Settings
- **Autonomous Scraping & Parsing:** Requests, HTTPAdapter Retry, BeautifulSoup4, Pandas
- **Natural Language Processing:** spaCy (Named Entity Recognition for technical skills)
- **Forecasting Models:** ARIMA, Prophet, N-BEATS, Temporal Fusion Transformer (TFT)
- **Graph Database:** Neo4j (Skill Knowledge Graph & implied competency traversal)
- **Embeddings & Vector Indexing:** BGE-M3 Dense Representations + FAISS Vector Search
- **Explainable Machine Learning:** SHAP (SHapley Additive exPlanations)

### Frontend
- **Framework:** React 18+ with TypeScript
- **Build Tool:** Vite (Ultra-fast HMR and bundling)
- **Routing:** React Router DOM v6
- **State Management:** React Context API + TanStack React Query
- **HTTP Client:** Axios (Pre-configured instances with JWT interceptors)
- **Visualizations:** Recharts / Chart.js

---

## 🏗 System Architecture & 4-Tier Backend Pattern

The backend follows a strict 4-tier layered architecture designed for modularity and isolation:

```
┌────────────────────────────────────────────────────────┐
│  1. API Layer (FastAPI Routers, Pydantic Schemas)      │
│     Validates incoming JSON payloads and handles HTTP  │
├────────────────────────────────────────────────────────┤
│  2. Service Layer (Orchestration & Business Logic)     │
│     Manages background threads, caches, and tasks      │
├────────────────────────────────────────────────────────┤
│  3. Agent Layer (Autonomous Agentic AI Technology)     │
│     OODA Loop: Sense → Orient → Plan → Act → Reflect   │
├────────────────────────────────────────────────────────┤
│  4. Model Layer (SQLAlchemy ORM & Database Engine)     │
│     PostgreSQL persistence, relations, and transactions│
└────────────────────────────────────────────────────────┘
```

---

## 🤖 Autonomous Data Collection Agent (Component 1)

The **Data Collection Agent** ([`data_collection_agent.py`](file:///e:/Sliit/Y4/RP/J26-DS-304/EmploreraLK/backend/app/components/forecasting/agents/data_collection_agent.py)) is an autonomous AI agent engineered to extract, normalize, deduplicate, and curate live job postings with full job descriptions from both **LinkedIn** and **TopJobs.lk** for the Job Market Demand Forecasting Engine.

### 🌐 Supported Platforms
1. **LinkedIn Guest Portal:**
   - Search Endpoint: `https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`
   - Job Detail & Full Description Endpoint: `https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}`
2. **TopJobs.lk (Sri Lanka Premier Job Portal):**
   - Base URL: `https://www.topjobs.lk`
   - Search Landing: `https://www.topjobs.lk/do.landing`
   - Vacancy Search: `https://www.topjobs.lk/applicant/vacancybyfunctionalarea.jsp` (IT category `FA=SDQ` + keyword queries)
   - Job Advertisement & Full Description: `https://www.topjobs.lk/employer/JobAdvertismentServlet?ac={ac}&jc={jc}&ec={ec}`

---

### 🔄 Multi-Stage Cross-Platform Deduplication Engine

When scraping across multiple platforms, employers frequently cross-post the identical opening on both LinkedIn and TopJobs. The agent incorporates a multi-tier deduplication engine:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      INCOMING JOB CANDIDATE                            │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  TIER 1: Exact ID & Canonical URL Match                │
        │  Checks job_id (li_*, tj_*) and clean URL against      │
        │  in-memory seen set and database index.                │
        └──────────────────────────┬─────────────────────────────┘
                                   │ [Not Matched]
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  TIER 2: Normalized Composite Fingerprint Match        │
        │  Strips legal suffixes ("(pvt) ltd", "private limited",│
        │  "sri lanka") & title noise ("(urgent)", "remote")     │
        │  Matches norm_title::norm_company hash.                │
        └──────────────────────────┬─────────────────────────────┘
                                   │ [Not Matched]
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  TIER 3: Fuzzy Cross-Platform Semantic Match           │
        │  Uses token Jaccard & SequenceMatcher similarity:      │
        │  - Company similarity >= 0.80                          │
        │  - Title similarity >= 0.78                            │
        │  - Composite weighted score >= similarity_threshold    │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                 ┌─────────────────┴─────────────────┐
                 │                                   │
          [Duplicate Detected]              [Confirmed Unique]
                 │                                   │
                 ▼                                   ▼
 ┌───────────────────────────────┐   ┌───────────────────────────────┐
 │ DROPPED / ENRICHED            │   │ COMMITTED TO MEMORY & DB      │
 │ Keeps primary post, enriches  │   │ Saves full title, company,    │
 │ metadata, increments merged   │   │ link, timestamps, and full    │
 │ telemetry count.              │   │ job description text.         │
 └───────────────────────────────┘   └───────────────────────────────┘
```

### Key Technical Capabilities:
1. **Full Job Description Ingestion:** Fetches and cleans text descriptions from LinkedIn and TopJobs, and preserves image-based TopJobs adverts for display. The full pipeline performs collection during the data stage (`fetch_full_description=True`); the NLP stage processes saved text and does not fetch portal pages itself.
2. **Self-Healing Cognition:** Detects HTTP 429 rate limits, triggers adaptive exponential backoff with randomized jitter (35s+), rotates browser session pools, and refreshes User-Agent fingerprints.
3. **Selector Fallback Tree:** Employs hierarchical CSS selectors to handle dynamic DOM layout shifts without crashing.
4. **Episodic Memory Bank:** Preloads database indexes to guarantee cross-session deduplication.
5. **Dual Persistence:** Commits clean records to Neon PostgreSQL (`job_postings`, `data_collection_runs`) and exports CSV datasets.


---

## 🧠 Autonomous NLP Extraction Agent (Component 1)

The **NLP Extraction Agent** ([`nlp_extraction_agent.py`](file:///e:/Sliit/Y4/RP/J26-DS-304/EmploreraLK/backend/app/components/forecasting/agents/nlp_extraction_agent.py)) is an autonomous AI agent engineered to extract, normalize, and categorize technical skills, soft skills, seniority levels, required experience years, and educational credentials from raw job advertisement descriptions.

### 📐 Multi-Engine Extraction Architecture

The agent combines statistical Named Entity Recognition with deterministic taxonomy lookups and heuristic pattern matchers:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   UNSTRUCTURED JOB ADVERTISEMENT TEXT                  │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  1. spaCy Linguistic Analysis Pipeline                 │
        │  Tokenization, Lemmatization, Entity Recognition       │
        │  (en_core_web_sm with resilient regex phrase fallback) │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  2. Curated IT Taxonomy & Contextual Boundary Engine   │
        │  Evaluates aliases across 8 core categories.           │
        │  Handles special symbols (C++, C#, .NET, Node.js) via  │
        │  negative lookbehind/lookahead (?<!\w)alias(?!\w).    │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  3. Metadata & Contextual Feature Extractors           │
        │  • Seniority Classifier (Intern → Junior → Mid →       │
        │    Senior → Lead → Manager/Executive)                  │
        │  • Experience Min-Years Parser (e.g., "3+ years")      │
        │  • Education Credential Detector (BSc, MSc, PhD, etc.) │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  4. Quality Scoring, Normalization & Persistence       │
        │  • Updates job_postings (status='extracted', skills)   │
        │  • Records execution metrics in nlp_extraction_runs    │
        └────────────────────────────────────────────────────────┘
```

### 🏷️ 8 Curated Skill Categories & Taxonomies
1. **Programming Languages:** Python, Java, C++, C#, TypeScript, JavaScript, Go, Rust, PHP, Ruby, Kotlin, Swift, Scala, R, SQL, Dart, Shell.
2. **Web & Backend Frameworks:** React, Angular, Vue.js, Node.js, Express, Django, FastAPI, Flask, Spring Boot, ASP.NET / .NET Core, Next.js, Laravel.
3. **Cloud, DevOps & Infrastructure:** AWS, Azure, Google Cloud (GCP), Docker, Kubernetes, Terraform, CI/CD, Linux, Jenkins, Ansible, Helm.
4. **Databases & Data Storage:** PostgreSQL, MySQL, MongoDB, Redis, Elasticsearch, Oracle, MS SQL Server, Cassandra, DynamoDB, Snowflake.
5. **AI, Data Science & Machine Learning:** Machine Learning, Deep Learning, NLP, PyTorch, TensorFlow, Computer Vision, Scikit-learn, LLMs, Pandas, Apache Spark.
6. **Testing, QA & Automation:** Selenium, JUnit, Cypress, Jest, PyTest, Postman, JMeter, Playwright, Cucumber, TestNG.
7. **Architecture & Engineering Methodologies:** Microservices, REST APIs, GraphQL, Agile / Scrum, CI/CD, Git, TDD, OOP, System Design, DevOps.
8. **Soft Skills & Professional Attributes:** Communication Skills, Team Collaboration, Leadership, Problem Solving, Analytical Thinking, Time Management.

### 🎯 Seniority, Experience & Education Classification
- **Seniority Classification:** Extracts explicit and implicit seniority markers (`intern`, `junior`, `mid`, `senior`, `lead`, `manager`) using weighted title and description keyword heuristics.
- **Experience Years Parser:** Extracts quantitative minimum experience requirements (`3+ years`, `5-7 years`, `at least 2 years` → `3`, `5`, `2`).
- **Education Level Parser:** Detects educational prerequisites (`Bachelor's Degree`, `Master's Degree`, `PhD / Doctorate`, `Diploma / HND`).

---

## ⚙️ Autonomous Skill Processing Agent (Component 1)

The **Skill Processing Agent** ([`skill_processing_agent.py`](file:///e:/Sliit/Y4/RP/J26-DS-304/EmploreraLK/backend/app/components/forecasting/agents/skill_processing_agent.py)) is an autonomous AI agent engineered to normalize noisy, fragmented skill tokens into canonical ontology representations, perform typo tolerance, deduce implicit parent competencies, score skill importance, and generate skill co-occurrence cluster networks for demand forecasting.

### 🔬 6 Automated Skill Processing Techniques

```
┌────────────────────────────────────────────────────────────────────────┐
│               RAW EXTRACTED SKILLS & JOB ADVERTISEMENT TITLE           │
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  1. Multi-Level Canonical Aliasing & Standardization   │
        │  Maps 87+ canonical IT skills across 6 domains and     │
        │  14 categories. Resolves variants (e.g., 'react.js',   │
        │  'reactjs', 'react js' -> 'React').                    │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  2. Fuzzy String Matching & Typo Tolerance             │
        │  Applies SequenceMatcher token similarity (>= 0.85)    │
        │  to correct misspellings (e.g. 'pyhton' -> 'Python',    │
        │  'dockr' -> 'Docker', 'postgress' -> 'PostgreSQL').     │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  3. Ontological Implication Deduction                 │
        │  Deduces implied competencies from specialized tools:  │
        │  • FastAPI / Django -> Python, RESTful APIs, Backend   │
        │  • React / Angular  -> JavaScript, Frontend Development│
        │  • Kubernetes       -> Docker, Container Orchestration │
        │  • PyTorch          -> Deep Learning, Machine Learning │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  4. Position-Based Importance Weighting (Core Skills)   │
        │  • Title Boost: 2.0x weight & flagged as Core Skill.   │
        │  • Body mentions: 1.0x weight.                         │
        │  • Implied competencies: 0.6x weight.                  │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  5. Hierarchical Taxonomy Classification               │
        │  Classifies into Domain -> Category -> Subcategory     │
        │  (e.g., Software Engineering -> Web Frameworks).       │
        └──────────────────────────┬─────────────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │  6. Co-occurrence Network & Clustering Matrix          │
        │  Computes pairwise co-occurrence frequencies across    │
        │  jobs to discover skill bundles and affinities.        │
        └────────────────────────────────────────────────────────┘
```

### 🏷️ 6 Taxonomy Domains & 14 Categories
1. **Software Engineering:** Programming Languages (19), Frontend Frameworks & UI (8), Backend Frameworks (10), Architecture & Methodologies (6).
2. **Cloud & DevOps:** Cloud Infrastructure (3), Containerization & Orchestration (2), CI/CD & Infrastructure as Code (5).
3. **Data Science & AI:** Machine Learning & AI (9), Data Engineering & Analytics (4).
4. **Databases & Storage:** Relational Databases (4), NoSQL & In-Memory (3).
5. **Quality Assurance & Testing:** Software Testing & Automation (8).
6. **Methodologies & Professional Skills:** Methodologies & Process (2), Soft Skills (4).

---

## 📝 API Endpoints Specification

### 1. Autonomous Data Collection, NLP Extraction, Skill Processing & Forecasting (Component 1)
| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/forecast/jobs/collect` | Deploy the autonomous agent to collect live jobs (sync or async background) |
| `GET` | `/api/forecast/agent/runs/{run_id}` | Check status, progress, and telemetry trace of an agent collection run |
| `GET` | `/api/forecast/agent/runs` | List recent autonomous agent collection runs |
| `GET` | `/api/forecast/jobs` | Query collected job postings (keyword, company, location, pagination) |
| `GET` | `/api/forecast/jobs/stats` | Aggregated data collection statistics & forecasting readiness |
| `POST` | `/api/forecast/nlp/extract` | Deploy NLP Extraction Agent over collected jobs (batch processing) |
| `POST` | `/api/forecast/nlp/extract-text` | Ad-hoc extraction of skills, seniority, experience, and education from raw text |
| `GET` | `/api/forecast/nlp/runs` | List recent autonomous NLP extraction agent runs |
| `GET` | `/api/forecast/nlp/runs/{run_id}` | Retrieve telemetry and metrics for a specific NLP extraction run |
| `GET` | `/api/forecast/nlp/skills/distribution` | Retrieve top in-demand skills and category distribution breakdown |
| `POST` | `/api/forecast/skills/process` | Deploy Skill Processing Agent over database jobs (batch or background) |
| `POST` | `/api/forecast/skills/normalize` | Normalize raw skills array (ad-hoc) with fuzzy typo matching & ontology deduction |
| `GET` | `/api/forecast/skills/runs` | List Skill Processing Agent execution runs |
| `GET` | `/api/forecast/skills/runs/{run_id}` | Retrieve execution report and telemetry trace for a specific skill run |
| `GET` | `/api/forecast/skills/taxonomy` | Retrieve full multi-tier hierarchical taxonomy tree |
| `GET` | `/api/forecast/skills/co-occurrences/{skill_name}` | Discover co-occurring skill clusters for a target technology |
| `GET` | `/api/v1/forecast/skills` | Retrieve longitudinal demand forecast for specified skills |
| `GET` | `/api/v1/forecast/emerging` | Identify emerging high-growth technologies |
| `GET` | `/api/v1/forecast/occupation/{id}` | Forecast aggregate demand for a specific job title |
| `POST` | `/api/v1/forecast/retrain` | Trigger retraining of time-series models with newly collected data |

### 2. Authentication & User Profile
| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/auth/signup` | Register a new user account (`seeker` or `recruiter`) |
| `POST` | `/api/auth/login` | Authenticate with credentials and receive JWT access token |
| `GET` | `/api/auth/me` | Retrieve profile of the currently authenticated user |
| `GET` | `/api/auth/google/login` | Initiate Google OAuth2 login redirect |
| `GET` | `/api/auth/google/callback` | Google OAuth2 authentication callback |
| `GET` | `/api/auth/linkedin/login` | Initiate LinkedIn OAuth2 login redirect |
| `GET` | `/api/auth/linkedin/callback` | LinkedIn OAuth2 authentication callback |
| `PUT` | `/api/profile/update` | Update target role, current role, and skills profile |

### 3. Skill Gap Discovery (Component 2)
| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/v1/skill-gap/discover` | Discover missing competencies for a candidate profile |
| `GET` | `/api/v1/skill-gap/report/{id}` | Retrieve comprehensive skill gap analysis report |

### 4. Career Path Planning (Component 3)
| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/v1/career-path/generate` | Generate optimal multi-step career trajectory roadmap |
| `GET` | `/api/v1/career-path/salary-forecast` | Forecast anticipated salary progression across milestones |

### 5. Semantic Skill Matching (Component 4)
| Method | Endpoint | Description |
|:---|:---|:---|
| `GET` | `/api/v1/matching/jobs` | Match candidate profile against collected vacancies |
| `GET` | `/api/v1/matching/score` | Compute cross-encoder alignment score between candidate and job |

---

## 📊 Database Schema (PostgreSQL via Neon Tech)

### Active Relational Tables

#### 1. `users`
- `id` (Integer, PK)
- `email` (String 255, Unique, Indexed)
- `hashed_password` (String 255, Nullable for OAuth)
- `name` (String 255)
- `role` (String 50: `seeker`, `recruiter`, `admin`)
- `google_id`, `linkedin_id`, `avatar_url` (OAuth metadata)
- `current_role`, `target_role`, `skills` (JSON text list)
- `company` (Recruiter organization)
- `is_active` (Boolean)
- `created_at`, `updated_at` (Timestamps with timezone)

#### 2. `job_postings`
- `id` (Integer, PK)
- `job_id` (String 128, Unique, Indexed — e.g. `li_4476810189`, `tj_185294`)
- `title` (String 255, Indexed)
- `company` (String 255, Indexed)
- `location` (String 255, Indexed)
- `job_link` (Text)
- `posted_date_text` (String 100 — e.g. `2 days ago`)
- `posted_timestamp` (DateTime UTC with timezone, Indexed)
- `source` (String 50: `LinkedIn`, `TopJobs`)
- `search_keyword` (String 255, Indexed)
- `status` (String 50: `collected`, `extracted`, `processed`)
- `quality_score` (Integer 0-100)
- `description_raw` (Text, Nullable)
- `skills_extracted` (Text JSON array of canonical skill names)
- `seniority_level` (String 50: `intern`, `junior`, `mid`, `senior`, `lead`, `manager`)
- `experience_years_min` (Integer, Nullable)
- `education_level` (String 100, Nullable)
- `skills_processed` (Text JSON dictionary with canonical skills, weights, implied competencies, and categories)
- `processed_at` (DateTime UTC with timezone, Nullable)
- `raw_metadata` (Text JSON dictionary)
- `created_at`, `updated_at` (Timestamps with timezone)

#### 3. `data_collection_runs`
- `id` (Integer, PK)
- `run_id` (String 64, Unique, Indexed)
- `source` (String 50: `LinkedIn`, `TopJobs`, `Multi-Source`)
- `target_keywords` (String 255)
- `target_location` (String 255)
- `target_count` (Integer)
- `collected_count` (Integer)
- `duplicate_count` (Integer)
- `status` (String 50: `running`, `completed`, `partial`, `rate_limited`, `failed`)
- `execution_summary` (Text JSON with full telemetry trace)
- `error_message` (Text, Nullable)
- `started_at`, `completed_at` (Timestamps with timezone)

#### 4. `nlp_extraction_runs`
- `id` (Integer, PK)
- `run_id` (String 64, Unique, Indexed)
- `total_processed` (Integer)
- `skills_extracted_count` (Integer)
- `unique_skills_count` (Integer)
- `status` (String 50: `running`, `completed`, `partial`, `failed`)
- `execution_summary` (Text JSON with extraction telemetry trace)
- `error_message` (Text, Nullable)
- `started_at`, `completed_at` (Timestamps with timezone)

#### 5. `skill_processing_runs`
- `id` (Integer, PK)
- `run_id` (String 64, Unique, Indexed)
- `total_processed` (Integer)
- `skills_normalized_count` (Integer)
- `unique_canonical_skills_count` (Integer)
- `status` (String 50: `pending`, `running`, `completed`, `failed`)
- `execution_summary` (Text JSON with telemetry, domain distribution, and co-occurrence pairs)
- `error_message` (Text, Nullable)
- `started_at`, `completed_at` (Timestamps with timezone)

---

## 🚀 Getting Started & Execution Guide

### Prerequisites
- Python 3.11+
- Node.js 18+
- Git
- Neon PostgreSQL database connection string

---

### 1. Backend Setup

```bash
# Clone the repository
git clone https://github.com/Sumudu01/J26-DS-304.git
cd J26-DS-304/EmploreraLK/backend

# Create and activate Python virtual environment
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install all backend dependencies
pip install -r requirements.txt

# Download spaCy English NLP model pipeline
python -m spacy download en_core_web_sm

# Configure environment variables
cp .env.example .env
```

Ensure your `.env` contains your Neon PostgreSQL credentials:
```env
DATABASE_URL=postgresql+psycopg2://<user>:<password>@<host>/<dbname>?sslmode=require
SECRET_KEY=emploreralk-super-secret-key-2026-sliit
PORT=5000
HOST=127.0.0.1
ENVIRONMENT=development
```

Start the FastAPI application:
```bash
uvicorn app.main:app --reload --port 5000
```
- Interactive Swagger UI: **http://localhost:5000/api/docs**
- ReDoc UI: **http://localhost:5000/api/redoc**
- OpenAPI Schema: **http://localhost:5000/api/openapi.json**

---

### 2. Running the Autonomous Data Collection Agent

#### Option A: Standalone CLI Runner (`run_agent.py`)
Run the autonomous agent directly from the command line across LinkedIn and TopJobs:

```bash
# Run agent across both LinkedIn & TopJobs.lk (with full descriptions & deduplication)
python run_agent.py --sources linkedin topjobs --keywords "Information Technology" --location "Sri Lanka" --max-jobs 50 --export-csv

# Gather data from TopJobs only
python run_agent.py --sources topjobs --keywords "Software Engineer" --max-jobs 20

# Gather data from LinkedIn only
python run_agent.py --sources linkedin --keywords "Data Scientist" --location "Sri Lanka" --max-jobs 20

# Offline standalone mode (CSV-only, no database required)
python run_agent.py --sources linkedin topjobs --keywords "Python Developer" --max-jobs 10 --no-db --csv-filename "jobs.csv"
```

#### Option B: REST API Deployment
Deploy the agent dynamically through the FastAPI endpoint:

```bash
# 1. Deploy autonomous agent across both portals in the background
curl -X POST http://localhost:5000/api/forecast/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{
    "sources": ["LinkedIn", "TopJobs"],
    "keywords": "Software Engineer",
    "location": "sri lanka",
    "max_jobs": 50,
    "fetch_full_description": true,
    "similarity_threshold": 0.85,
    "background": true
  }'

# 2. Check telemetry, progress, and deduplication status of the agent run
curl -X GET http://localhost:5000/api/forecast/agent/runs/{run_id}

# 3. Query collected jobs from the database (filtered by keyword, location, or source)
curl -X GET "http://localhost:5000/api/forecast/jobs?keyword=Software&source=TopJobs&page=1&page_size=20"

# 4. View aggregated collection stats and platform breakdown
curl -X GET http://localhost:5000/api/forecast/jobs/stats
```

---

### 3. Running the Autonomous NLP Extraction Agent

#### Option A: Standalone CLI Runner (`run_nlp_agent.py`)
Run the autonomous NLP agent directly from the command line over collected database records or ad-hoc texts:

```bash
# Extract skills from pending unextracted job postings in the database
python run_nlp_agent.py --batch-size 25

# Force re-extraction across all job postings in the database
python run_nlp_agent.py --batch-size 50 --force-reextract

# Filter extraction to jobs collected from a specific source (e.g. TopJobs)
python run_nlp_agent.py --source TopJobs --batch-size 20

# Test ad-hoc extraction on a custom job description string
python run_nlp_agent.py --test-title "Senior Full-Stack Engineer" \
  --test-text "We are seeking a Senior Developer with 5+ years of experience in Python, FastAPI, Docker, and AWS. Bachelor's Degree in Computer Science required."
```

#### Option B: REST API Deployment
Deploy the NLP agent dynamically via FastAPI endpoints:

```bash
# 1. Trigger NLP extraction across pending database jobs (batch or background)
curl -X POST http://localhost:5000/api/forecast/nlp/extract \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 25,
    "force_reextract": false,
    "background": true
  }'

# 2. Extract skills and metadata from ad-hoc text on demand
curl -X POST http://localhost:5000/api/forecast/nlp/extract-text \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Lead DevOps Architect",
    "text": "Seeking a Lead Cloud Engineer with 8+ years experience in Kubernetes, Terraform, AWS, CI/CD, and Python. Master degree in Computer Science preferred."
  }'

# 3. Check status and telemetry of an NLP extraction run
curl -X GET http://localhost:5000/api/forecast/nlp/runs/{run_id}

# 4. View aggregated skill frequency distribution and categories
curl -X GET "http://localhost:5000/api/forecast/nlp/skills/distribution?limit=20"
```

---

### 4. Running the Autonomous Skill Processing Agent

#### Option A: Standalone CLI Runner (`run_skill_agent.py`)
Run the autonomous skill normalizer directly from the command line:

```bash
# 1. Process and normalize pending job postings from the database
python run_skill_agent.py --batch-size 25

# 2. Force re-processing across all job postings in the database
python run_skill_agent.py --batch-size 50 --force-reprocess

# 3. Test ad-hoc normalization on noisy tokens with context title boost
python run_skill_agent.py --test-skills pyhton "react js" k8s postgress fastapi dockr \
  --test-title "Senior Python & Cloud Architect"

# 4. Query co-occurring skill cluster relationships for a target skill
python run_skill_agent.py --query-cooccurrence Python

# 5. Display hierarchical taxonomy tree breakdown
python run_skill_agent.py --show-taxonomy
```

#### Option B: REST API Deployment
Deploy the Skill Processing Agent dynamically via FastAPI endpoints:

```bash
# 1. Trigger automated skill processing on database jobs (sync or async background)
curl -X POST http://localhost:5000/api/forecast/skills/process \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 25,
    "force_reprocess": false,
    "fuzzy_threshold": 0.85,
    "enable_implication": true,
    "background": true
  }'

# 2. Normalize an arbitrary skills array on demand
curl -X POST http://localhost:5000/api/forecast/skills/normalize \
  -H "Content-Type: application/json" \
  -d '{
    "skills": ["pyhton", "react js", "k8s", "postgress"],
    "job_title": "Senior Python Architect",
    "fuzzy_threshold": 0.85,
    "enable_implication": true
  }'

# 3. Check status and telemetry of a skill processing run
curl -X GET http://localhost:5000/api/forecast/skills/runs/{run_id}

# 4. Retrieve complete multi-tier hierarchical taxonomy tree
curl -X GET http://localhost:5000/api/forecast/skills/taxonomy

# 5. Query top co-occurring skills and cluster affinity for a technology
curl -X GET "http://localhost:5000/api/forecast/skills/co-occurrences/Python?limit=15"
```

---

### 5. Frontend Setup

```bash
cd J26-DS-304/EmploreraLK/frontend

# Install dependencies
npm install

# Configure environment variables
cp .env.example .env

# Run Vite dev server
npm run dev
```

Frontend application will be accessible at: **http://localhost:5173**

---

## 🔐 Security & Compliance

- **Environment Isolation:** Secrets and database credentials are managed exclusively via `.env`.
- **Password Hashing:** Passlib with Bcrypt algorithm.
- **JWT Protection:** HS256-signed stateless authentication tokens.
- **Anti-Bot Politeness:** Automated request pacing, randomized jitter, exponential backoff, and header rotation.
- **Data Anonymization:** Candidate resumes and user PII are sanitized in accordance with academic research standards.

---

## 📄 License & Academic Integrity

This project is developed for academic purposes as part of the Final Year Research Project requirements for the B.Sc. (Hons) in Information Technology specializing in Data Science at SLIIT.

---

## 📞 Contact

**Project Lead / Team Email:** [emploreralk@gmail.com](mailto:emploreralk@gmail.com)  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT), Malabe, Sri Lanka.
