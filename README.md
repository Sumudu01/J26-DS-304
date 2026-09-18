# Emploreralk

### AI-Based Skill Analysis and Skill Matching Recruitment System

A comprehensive AI-driven recruitment intelligence platform for Sri Lanka's IT sector, integrating demand forecasting, skill gap discovery, career path planning, and semantic job matching.

## 📋 Project Overview

**Project Name:** Emploreralk  
**Project Code:** J26-DS-304  
**Academic Year:** 2026 - Final Year Research Project  
**Course:** B.Sc. (Hons) in Information Technology specialized in Data Science  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT)

This platform provides a unified system for predicting future skill demand, discovering hidden skill gaps, generating personalized career pathways, and matching candidates to job opportunities using AI, agentic AI, and explainable machine learning.

---

## 👥 Team Members

| Student ID | Name | Role/Module |
|------------|------|-------------|
| IT23187382 | Wijeratne U.G.S.L. | Job Market Demand Forecasting Engine |
| IT23374324 | Mathumitha E. | Hidden Skill Gap Discovery Engine |
| IT23218994 | Athuraliya D.S. | Career Path Planning and Optimization Engine |
| IT23151406 | Sandanayaka S.D.P.D. | Skill Matching and Job Alignment Engine |

---

## 👨‍🏫 Supervisors

| Role | Name |
|------|------|
| Supervisor | Prof. Samantha Thelijjagoda |
| Co-Supervisor | Mr. Samadhi Rathnayake |
| External Supervisor | Prof. Nishantha Giguruwa |

---

## 🛠 Technology Stack

### Backend
- **Framework:** FastAPI (Modern, high-performance Python web framework)
- **Language:** Python 3.11+ (Latest stable with async support)
- **Database:** PostgreSQL 15 via Neon Tech (Serverless relational database)
- **ORM:** SQLAlchemy (Python SQL toolkit and ORM)
- **Validation:** Pydantic (Data validation and settings management)
- **Web Scraping:** BeautifulSoup + Scrapy (HTML parsing and crawling)
- **NLP:** spaCy (Named Entity Recognition and text processing)
- **Forecasting:** ARIMA, Prophet, N-BEATS, Temporal Fusion Transformer (TFT)
- **Graph Database:** Neo4j (Skill Knowledge Graph)
- **Embeddings:** BGE-M3 (Semantic representation)
- **Vector Search:** FAISS (Efficient similarity search)
- **Explainable AI:** SHAP (SHapley Additive exPlanations)

### Frontend
- **Framework:** React 18+ (Component-based UI library)
- **Build Tool:** Vite (Modern, fast frontend build tool)
- **Language:** TypeScript (Type-safe JavaScript)
- **Routing:** React Router 6.x (Declarative routing)
- **State Management:** React Context API + React Query
- **HTTP Client:** Axios (Promise-based API communication)
- **Visualization:** Recharts / Chart.js (Data visualization)
- **Styling:** Modular CSS & Responsive Layouts (Flexbox/Grid)

### DevOps & Tools
- **Database Hosting:** Neon Tech (Serverless PostgreSQL)
- **Version Control:** Git with Branching Strategy
- **Documentation:** README & API Specifications
- **Development Environment:** VS Code

---

## 🏗 System Architecture & Design Patterns

### 1. Modular Layered Architecture (Backend)
The backend follows a strict 4-tier layered architecture to ensure separation of concerns and maintainability:
- **API Layer:** FastAPI routers handle incoming JSON requests, perform Pydantic validation, and return structured responses.
- **Service Layer:** Contains core business logic, agent orchestration, and cross-component integrations.
- **Agent Layer:** Four specialized autonomous agents for data collection, NLP extraction, skill processing, and insight generation.
- **Model Layer:** SQLAlchemy ORM entities and Pydantic schemas for database and API interactions.

### 2. Frontend Component Architecture
- **Atomic Components:** Reusable UI elements (Buttons, Inputs, Cards, Charts).
- **Page Components:** Complex views that manage local state and fetch data (Dashboard, ForecastExplorer, SkillGap, CareerPath, JobMatches).
- **Context Providers:** Centralized state for Authentication and UI preferences.
- **API Service Layer:** Abstracted Axios instances for clean communication with backend endpoints.

---

## 🧠 Core Implementation Techniques

### 🤖 Agentic AI Pipeline
The forecasting engine employs four specialized autonomous agents:
1. **Data Collection Agent** — Autonomously scrapes job postings from LinkedIn, TopJobs, and Ikman.lk using BeautifulSoup and LinkedIn Guest API.
2. **NLP Extraction Agent** — Extracts structured skill data using spaCy NER and performs job ad deduplication.
3. **Skill Processing Agent** — Normalizes skills using a curated taxonomy and constructs time-series data matrices.
4. **Insight Generation Agent** — Applies ARIMA, Prophet, N-BEATS, and TFT models to forecast future skill demand with SHAP explainability.

### 📈 Longitudinal Time Series Forecasting
- **ARIMA:** Captures linear trends and seasonality.
- **Prophet:** Handles holiday effects, changepoints, and missing data.
- **N-BEATS:** Deep learning-based univariate forecasting.
- **Temporal Fusion Transformer (TFT):** Multi-horizon forecasting with interpretable attention mechanisms.

### 🧩 Skill Knowledge Graph
- **Neo4j Integration:** Models skill dependencies, prerequisites, and transferable competencies.
- **Graph-Based Reasoning:** Infers implied skills and adjacent competencies.

### 🔍 Multi-Stage Semantic Matching
- **BGE-M3 Embeddings:** Semantic representation of skills and job descriptions.
- **FAISS Retrieval:** Efficient similarity search for candidate-job alignment.
- **Cross Encoder Re-ranking:** Fine-grained accuracy for final match scoring.
- **Explainable AI:** Transparent reasoning for all matching decisions.

### 🌐 Global Error Handling
- **FastAPI Exception Handlers:** Centralized exception handling for clean, consistent JSON error responses.
- **Custom Exceptions:** Domain-specific exceptions for precise error reporting.

---

## 📝 API Endpoints Detailed

### 🔑 Forecast & Demand Prediction
- `GET /api/v1/forecast/skills` - Get skill demand forecasts for specified skills.
- `GET /api/v1/forecast/emerging` - Identify emerging skills before they become mainstream.
- `GET /api/v1/forecast/occupation/{id}` - Forecast demand for a specific occupation.
- `POST /api/v1/forecast/retrain` - Trigger model retraining with latest data.

### 📊 Skill Gap Discovery (Member 2)
- `GET /api/v1/skill-gap/discover` - Discover skill gaps for a candidate profile.
- `GET /api/v1/skill-gap/report/{id}` - Retrieve personalized skill gap report.

### 🛤️ Career Path Planning (Member 3)
- `GET /api/v1/career-path/generate` - Generate personalized career roadmap.
- `GET /api/v1/career-path/salary-forecast` - Forecast salary progression for pathways.

### 🎯 Skill Matching (Member 4)
- `GET /api/v1/matching/jobs` - Match candidate profile to job opportunities.
- `GET /api/v1/matching/score` - Get compatibility score between candidate and job.

---

## 🏗 Architecture

### Backend Architecture (Layered)
```
┌─────────────────────────────────────────┐
│           API Layer                     │
│    (FastAPI Routers, Pydantic Schemas)  │
├─────────────────────────────────────────┤
│            Service Layer                │
│    (Business Logic, Orchestration)      │
├─────────────────────────────────────────┤
│            Agent Layer                  │
│   (Data Collection, NLP, Skill, Insight)│
├─────────────────────────────────────────┤
│            Model Layer                  │
│    (SQLAlchemy Models, Repositories)    │
└─────────────────────────────────────────┘
```

### Frontend Architecture
```
┌─────────────────────────────────────────┐
│           Pages/Views                   │
│  (Dashboard, Forecast, SkillGap,        │
│   CareerPath, JobMatches)               │
├─────────────────────────────────────────┤
│         Components                      │
│   (Reusable UI Elements, Charts)        │
├─────────────────────────────────────────┤
│        Services/API Layer               │
│      (Axios Client, API Integration)    │
├─────────────────────────────────────────┤
│         Context/State                   │
│   (Auth Context, React Query Cache)     │
└─────────────────────────────────────────┘
```

---

## 📊 Database Schema

### Core Tables (Forecasting Engine)
- **job_postings** - Raw scraped job postings from multiple platforms
- **skill_demand_indices** - Monthly skill demand time-series data
- **forecast_results** - Model predictions with confidence intervals
- **skill_taxonomy** - Normalized skill dictionary and mappings
- **candidate_profiles** - Parsed resume data (shared)
- **career_paths** - Recommended pathways (shared)
- **job_matches** - Matching scores and alignments (shared)

---

## 🔐 Security Features

- Data anonymization for all candidate information
- Environment variable management for secrets
- CORS configuration for frontend-backend communication
- Input validation and sanitization via Pydantic
- GDPR/CCPA compliance for data handling

---

## 🚀 Getting Started

### Prerequisites

Ensure the following are installed:

- Python 3.11+
- Node.js 18+
- Git
- Neon Tech account (free tier available)

### Option 1: Manual Development Setup (Recommended)

#### Backend Setup

```bash
# Clone the repository
git clone <repository-url>
cd J26-DS-304

# Navigate to backend
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env with your Neon DATABASE_URL and other secrets
# DATABASE_URL=postgresql://user:password@host/dbname?sslmode=require

# Run the backend
uvicorn app.main:app --reload
```

Backend will be available at: **http://localhost:8000**  
API documentation: **http://localhost:8000/docs**

#### Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env

# Run the frontend
npm run dev
```

Frontend will be available at: **http://localhost:5173**

---

### Option 2: Running with Docker (Optional)

```bash
# Start all services
docker-compose up --build

# Start in background
docker-compose up -d --build

# Stop all services
docker-compose down

# View logs
docker-compose logs -f
```

---

### Environment Variables Required

Create a `.env` file in `backend/` with:

```env
# Database Configuration (Neon Tech)
DATABASE_URL=postgresql://user:password@ep-xxx-xxx.region.aws.neon.tech/emploreralk?sslmode=require

# FastAPI
HOST=0.0.0.0
PORT=8000
DEBUG=True
SECRET_KEY=your_secret_key_here

# Model Configuration
MODEL_PATH=./data/models
FORECAST_HORIZON_MONTHS=24

# LinkedIn Guest API (optional)
LINKEDIN_API_KEY=your_api_key
```

Create a `.env` file in `frontend/` with:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_ENVIRONMENT=development
```

---

### Database Setup (Neon Tech)

1. Sign up at [neon.tech](https://neon.tech)
2. Create a new project
3. Copy the connection string from the dashboard
4. Paste it into `backend/.env` as `DATABASE_URL`
5. Run migrations:
   ```bash
   cd backend
   alembic upgrade head
   ```

---

## 📄 License

This project is developed for academic purposes as part of the final year research project requirements at SLIIT.

---

## 📞 Contact

**Email:** emploreralk@gmail.com

For questions or issues, please contact the development team through the university LMS or GitHub repository.

