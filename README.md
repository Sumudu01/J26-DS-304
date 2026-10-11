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
    │   │   │       ├── forecast.py          # Data Collection Agent & Forecasting routes
    │   │   │       ├── career_path.py       # Career pathway endpoints
    │   │   │       ├── skill_gap.py         # Skill gap discovery endpoints
    │   │   │       └── matching.py          # Candidate-to-job matching endpoints
    │   │   ├── components/                  # Domain Business Logic & AI Agents
    │   │   │   ├── forecasting/             # Component 1: Forecasting & Scraping
    │   │   │   │   ├── agents/
    │   │   │   │   │   ├── data_collection_agent.py   # Autonomous LinkedIn Data Collection Agent
    │   │   │   │   │   ├── nlp_extraction_agent.py    # NER Skill Extractor & Deduplication
    │   │   │   │   │   ├── skill_processing_agent.py  # Taxonomy Normalizer
    │   │   │   │   │   └── insight_generation_agent.py # Forecast Explainer
    │   │   │   │   ├── services/
    │   │   │   │   │   ├── scraping_service.py        # Background task & collection manager
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
    │   │   │   └── job_posting.py           # Job postings & Agent collection runs tables
    │   │   ├── schemas/                     # Pydantic Validation Schemas
    │   │   │   ├── auth.py                  # Auth request & response schemas
    │   │   │   └── job_posting.py           # Job posting & Agent goal/telemetry schemas
    │   │   ├── utils/                       # Common utilities & helpers
    │   │   └── main.py                      # FastAPI application entrypoint & lifespan
    │   ├── run_agent.py                     # Standalone CLI runner for Data Collection Agent
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

The **Data Collection Agent** (`app/components/forecasting/agents/data_collection_agent.py`) is an autonomous AI agent engineered to extract, normalize, and curate live job postings from LinkedIn's guest endpoints and web sources for demand forecasting.

### 🔄 Autonomous Perception-Cognition-Action Loop (OODA)

```
       ┌──────────────────────────────────────────────┐
       │             1. GOAL PERCEPTION               │
       │ Reads keyword criteria, probes network       │
       │ & loads database memory (known job IDs)      │
       └──────────────────────┬───────────────────────┘
                              │
                              ▼
       ┌──────────────────────────────────────────────┐
       │         2. SENSORY ORIENTATION               │
       │ Observes HTTP status (200, 429, 403, 500)    │
       │ & assesses response freshness / anti-bot     │
       └──────────────────────┬───────────────────────┘
                              │
               ┌──────────────┴──────────────┐
               │                             │
    [HTTP 429 Rate Limited]          [HTTP 200 OK]
               │                             │
               ▼                             ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ 3. SELF-HEALING REFLECTION  │ │ 4. EXTRACTION & EVALUATION  │
│ - Exponential backoff +     │ │ - Selector Fallback Tree    │
│   random jitter (35s+)      │ │ - Canonical URL cleaning    │
│ - Session connection reset  │ │ - ISO UTC timestamp parse   │
│ - User-Agent pool rotation  │ │ - Quality score calculation │
└──────────────┬──────────────┘ └──────────────┬──────────────┘
               │                               │
               └──────────────┬────────────────┘
                              │
                              ▼
       ┌──────────────────────────────────────────────┐
       │        5. MEMORY DEDUPLICATION & ACTION      │
       │ Skips already-seen IDs, persists new rows to │
       │ PostgreSQL (job_postings, runs) & writes CSV │
       └──────────────────────────────────────────────┘
```

### Key Technical Features:
1. **Endpoint Resolution:** Communicates with LinkedIn's guest search API (`https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search`).
2. **Autonomous Rate-Limit Mitigation:** Senses HTTP 429 status codes and initiates automated cooldowns with randomized jitter (35s+) combined with browser pool header rotation.
3. **Selector Fallback Tree:** Employs hierarchical CSS selectors to handle dynamic DOM layout shifts without crashing.
4. **Deterministic Unique Job IDs:** Extracts LinkedIn entity URN (`data-entity-urn`), clean URL ID patterns (`/view/12345`), or fallback SHA-256 canonical hashes.
5. **Episodic Deduplication Memory:** Preloads database indexes to ensure jobs already stored in PostgreSQL are never redundantly written.
6. **Telemetry & Audit Ledger:** Logs step-by-step reasoning (`thought`, `action`, `observation`) into `data_collection_runs`.

---

## 📝 API Endpoints Specification

### 1. Autonomous Data Collection & Forecasting (Component 1)
| Method | Endpoint | Description |
|:---|:---|:---|
| `POST` | `/api/forecast/jobs/collect` | Deploy the autonomous agent to collect live jobs (sync or async background) |
| `GET` | `/api/forecast/agent/runs/{run_id}` | Check status, progress, and telemetry trace of an agent run |
| `GET` | `/api/forecast/agent/runs` | List recent autonomous agent collection runs |
| `GET` | `/api/forecast/jobs` | Query collected job postings (keyword, company, location, pagination) |
| `GET` | `/api/forecast/jobs/stats` | Aggregated data collection statistics & forecasting readiness |
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
- `job_id` (String 128, Unique, Indexed — e.g. `li_4476810189`)
- `title` (String 255, Indexed)
- `company` (String 255, Indexed)
- `location` (String 255, Indexed)
- `job_link` (Text)
- `posted_date_text` (String 100 — e.g. `2 days ago`)
- `posted_timestamp` (DateTime UTC with timezone, Indexed)
- `source` (String 50: `LinkedIn`, `TopJobs`, etc.)
- `search_keyword` (String 255, Indexed)
- `status` (String 50: `collected`, `extracted`, `processed`)
- `quality_score` (Integer 0-100)
- `description_raw` (Text, Nullable)
- `raw_metadata` (Text JSON dictionary)
- `created_at`, `updated_at` (Timestamps with timezone)

#### 3. `data_collection_runs`
- `id` (Integer, PK)
- `run_id` (String 64, Unique, Indexed)
- `source` (String 50: `LinkedIn`)
- `target_keywords` (String 255)
- `target_location` (String 255)
- `target_count` (Integer)
- `collected_count` (Integer)
- `duplicate_count` (Integer)
- `status` (String 50: `running`, `completed`, `partial`, `rate_limited`, `failed`)
- `execution_summary` (Text JSON with full telemetry trace)
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
Run the autonomous agent directly from the command line:

```bash
# Run agent with default settings (Information Technology, Sri Lanka, 50 jobs)
python run_agent.py --keywords "Information Technology" --location "Sri Lanka" --max-jobs 50 --export-csv

# Gather data for specific roles (e.g. Data Scientist)
python run_agent.py --keywords "Data Scientist" --location "Sri Lanka" --max-jobs 25

# Offline mode without database connection (CSV-only)
python run_agent.py --keywords "Software Engineer" --location "Sri Lanka" --max-jobs 10 --no-db --csv-filename "jobs.csv"
```

#### Option B: REST API Deployment
Deploy the agent dynamically through the FastAPI endpoint:

```bash
# 1. Deploy autonomous agent asynchronously in the background
curl -X POST http://localhost:5000/api/forecast/jobs/collect \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "Software Engineer",
    "location": "sri lanka",
    "max_jobs": 50,
    "background": true
  }'

# 2. Check telemetry and status of the agent run
curl -X GET http://localhost:5000/api/forecast/agent/runs/{run_id}

# 3. Query collected jobs from the database
curl -X GET "http://localhost:5000/api/forecast/jobs?keyword=Software&location=Colombo&page=1&page_size=20"

# 4. View aggregated collection stats
curl -X GET http://localhost:5000/api/forecast/jobs/stats
```

---

### 3. Frontend Setup

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
