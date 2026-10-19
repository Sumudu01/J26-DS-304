import json
import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.database import engine, SessionLocal
from app.models.user import User
from app.models import Base
from app.core.security import get_password_hash
from app.api.v1 import api_router

# ─── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("emploreralk")


# ─── Demo seed data ─────────────────────────────────────────────────────────
DEMO_USERS = [
    {
        "name": "Alex (Demo Seeker)",
        "email": "seeker@emploeralk.com",
        "password": "password",
        "role": "seeker",
        "current_role": "Junior Developer",
        "target_role": "AI Engineer",
        "skills": json.dumps(["Python", "SQL", "Git", "HTML", "CSS"]),
        "company": None,
    },
    {
        "name": "Sam (Demo Recruiter)",
        "email": "recruiter@emploeralk.com",
        "password": "password",
        "role": "recruiter",
        "current_role": None,
        "target_role": None,
        "skills": json.dumps([]),
        "company": "Axiata LABS",
    },
    {
        "name": "Admin User",
        "email": "admin@emploeralk.com",
        "password": "password",
        "role": "admin",
        "current_role": None,
        "target_role": None,
        "skills": json.dumps([]),
        "company": None,
    },
]


def seed_demo_users(db) -> None:
    """Insert demo accounts if they don't exist. Idempotent."""
    for demo in DEMO_USERS:
        existing = db.query(User).filter(User.email == demo["email"]).first()
        if not existing:
            user = User(
                name=demo["name"],
                email=demo["email"],
                hashed_password=get_password_hash(demo["password"]),
                role=demo["role"],
                current_role=demo["current_role"],
                target_role=demo["target_role"],
                skills=demo["skills"],
                company=demo["company"],
                is_active=True,
            )
            db.add(user)
            logger.info("Seeded demo user: %s", demo["email"])
    db.commit()


# ─── Lifespan (startup / shutdown) ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks: create DB tables and seed demo users."""
    logger.info("Starting EmploreraLK API...")

    # Create all tables in Neon PostgreSQL (no-op if already exist)
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created / verified.")
    except Exception as exc:
        logger.error("Failed to create database tables: %s", exc)
        raise

    # Seed demo accounts
    db = SessionLocal()
    try:
        seed_demo_users(db)
        logger.info("Demo users seeded successfully.")
    except Exception as exc:
        logger.warning("Could not seed demo users: %s", exc)
    finally:
        db.close()

    logger.info(
        "EmploreraLK API is ready on http://%s:%s",
        settings.HOST,
        settings.PORT,
    )
    yield
    logger.info("EmploreraLK API shutting down.")


# ─── App factory ────────────────────────────────────────────────────────────
app = FastAPI(
    title="EmploreraLK API",
    description="AI-Based Skill Analysis and Skill Matching Recruitment System — Backend API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)


# ─── CORS Middleware ─────────────────────────────────────────────────────────
cors_origins = settings.CORS_ORIGINS if isinstance(settings.CORS_ORIGINS, list) else ["*"]
if "*" not in cors_origins:
    cors_origins.append("*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Custom exception handlers ───────────────────────────────────────────────
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Format HTTPExceptions as { "error": "...", "detail": "..." } for the frontend."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Format Pydantic validation errors as { "error": "...", "detail": [...] } for the frontend."""
    errors = exc.errors()
    # Build a human-readable summary
    messages = []
    for err in errors:
        field = " → ".join(str(loc) for loc in err.get("loc", []))
        msg = err.get("msg", "Invalid value")
        messages.append(f"{field}: {msg}" if field else msg)
    summary = "; ".join(messages)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": summary, "detail": errors},
    )


# ─── Mount API routes ────────────────────────────────────────────────────────
# Frontend calls http://127.0.0.1:5000/api/auth/signup, /api/auth/login, etc.
app.include_router(api_router, prefix="/api")


# ─── Health check endpoints ──────────────────────────────────────────────────
@app.get("/", tags=["Health"])
@app.get("/api/health", tags=["Health"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "service": "EmploreraLK API",
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
    }

