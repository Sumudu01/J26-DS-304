import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy import inspect, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_db
from app.api.v1 import skill_gap as skill_gap_api
from app.components.skill_gap import candidate_collection_service as service
from app.components.skill_gap.models import CandidateCollectionRun, CandidateProfile
from app.components.skill_gap.models import ensure_candidate_ownership_columns
from app.core.database import Base
from app.main import app
from app.models.job_posting import JobPosting
from app.models.user import User


class FakeResponse:
    def __init__(self, text="", status_code=200):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise service.requests.HTTPError(f"HTTP {self.status_code}")


def test_public_url_normalizes_github_and_rejects_unsupported_or_private(monkeypatch):
    assert service._public_url("https://github.com/octocat?tab=repositories") == (
        "https://github.com/octocat",
        "github",
    )
    with pytest.raises(service.CandidateCollectionError, match="LinkedIn"):
        service._public_url("https://www.linkedin.com/in/example")

    monkeypatch.setattr(
        service.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 443))],
    )
    with pytest.raises(service.CandidateCollectionError, match="Private"):
        service._public_url("https://portfolio.example/profile")


def test_portfolio_extraction_checks_robots_and_redacts_contact_details(monkeypatch):
    monkeypatch.setattr(
        service.socket,
        "getaddrinfo",
        lambda *args, **kwargs: [(None, None, None, None, ("93.184.216.34", 443))],
    )
    responses = iter([
        FakeResponse("User-agent: *\nAllow: /"),
        FakeResponse(
            '<html><head><title>Profile</title>'
            '<meta name="description" content="Python developer email me dev@example.com">'
            '</head><body><h1>Casey Candidate</h1><p>Python, FastAPI, PostgreSQL</p></body></html>'
        ),
    ])
    monkeypatch.setattr(service.requests, "get", lambda *args, **kwargs: next(responses))

    candidate = service.collect_profile("https://portfolio.example/profile")

    assert candidate["full_name"] == "Casey Candidate"
    assert candidate["source"] == "Portfolio"
    assert "dev@example.com" not in candidate["bio"]
    assert "[redacted]" in candidate["bio"]
    assert {"Python", "FastAPI", "PostgreSQL"}.issubset(candidate["skills"])


def test_collection_run_persists_candidate_data_and_status(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    request_db = test_session()
    run = service.create_collection_run(request_db, ["https://github.com/octocat"], owner_user_id=101)
    request_db.close()
    monkeypatch.setattr(service, "SessionLocal", test_session)
    monkeypatch.setattr(
        service,
        "collect_profile",
        lambda url: {
            "source_url": "https://github.com/octocat",
            "source": "GitHub",
            "full_name": "Octocat",
            "headline": "Python developer",
            "location": None,
            "bio": "Python developer",
            "skills": ["Python"],
            "projects": [{"name": "hello-world"}],
            "raw_data": {"public_repositories": 1},
        },
    )

    service.collect_run(run.run_id, ["https://github.com/octocat"])

    db = test_session()
    persisted_run = db.query(CandidateCollectionRun).filter_by(run_id=run.run_id).one()
    candidate = db.query(CandidateProfile).filter_by(source_url="https://github.com/octocat").one()
    assert persisted_run.status == "completed"
    assert persisted_run.collected_count == 1
    assert persisted_run.failed_count == 0
    assert json.loads(candidate.skills_json) == ["Python"]
    assert json.loads(candidate.raw_json) == {"public_repositories": 1}
    db.close()
    engine.dispose()


def test_collection_endpoint_is_seeker_scoped_and_queues_work(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    current_user = {"id": 1, "role": "seeker"}
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: User(id=current_user["id"], role=current_user["role"])
    monkeypatch.setattr(skill_gap_api, "collect_run", lambda *args: None)
    client = TestClient(app)
    try:
        payload = {"profile_urls": ["https://github.com/octocat"]}
        accepted = client.post("/api/skill-gap/candidates/collect", json=payload)
        assert accepted.status_code == 202
        assert accepted.json()["status"] == "queued"
        assert accepted.json()["requested_count"] == 1
        run_id = accepted.json()["run_id"]

        current_user["id"] = 2
        assert client.get(f"/api/skill-gap/candidate-collections/{run_id}").status_code == 404
        assert client.get("/api/skill-gap/candidates").json()["total"] == 0

        current_user["role"] = "recruiter"
        denied = client.post("/api/skill-gap/candidates/collect", json=payload)
        assert denied.status_code == 403
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_skill_gap_analysis_compares_profile_with_matching_job_skills():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = test_session()
        try:
            yield db
        finally:
            db.close()

    db = test_session()
    db.add(JobPosting(
        job_id="data-scientist-test",
        title="Data Scientist",
        company="Example Co",
        job_link="https://jobs.example/data-scientist",
        search_keyword="Data Scientist",
        skills_extracted=json.dumps(["Python", "SQL", "TensorFlow"]),
    ))
    db.commit()
    db.close()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: User(id=1, role="seeker", skills='["Python"]')
    try:
        response = TestClient(app).post("/api/skill-gap", json={"skills": [], "target_role": "Data Scientist"})
        assert response.status_code == 200
        result = response.json()
        assert result["match_percentage"] == 33
        assert result["matching_skills"] == ["Python"]
        assert result["missing_skills"] == ["SQL", "TensorFlow"]
        assert result["skill_roadmap"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()


def test_startup_upgrade_adds_ownership_columns_to_legacy_tables():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE candidate_profiles (id INTEGER PRIMARY KEY, source_url TEXT)"))
        connection.execute(text("CREATE TABLE candidate_collection_runs (id INTEGER PRIMARY KEY, run_id TEXT)"))

    ensure_candidate_ownership_columns(engine)
    ensure_candidate_ownership_columns(engine)

    inspector = inspect(engine)
    for table_name in ("candidate_profiles", "candidate_collection_runs"):
        assert "owner_user_id" in {column["name"] for column in inspector.get_columns(table_name)}
    engine.dispose()