import base64
import ipaddress
import json
import logging
import re
import socket
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.components.skill_gap.models import CandidateCollectionRun, CandidateProfile

logger = logging.getLogger("emploreralk.skill_gap.candidate_collection")

USER_AGENT = "EmploreraLK-CandidateCollector/1.0 (public-profile collection)"
REQUEST_TIMEOUT = 10
TECH_SKILLS = (
    "Python", "Java", "JavaScript", "TypeScript", "C++", "C#", "Go", "Rust",
    "PHP", "Ruby", "Swift", "Kotlin", "SQL", "PostgreSQL", "MySQL", "MongoDB",
    "React", "Angular", "Vue", "Node.js", "Django", "Flask", "FastAPI", "Spring",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "TensorFlow", "PyTorch",
    "Machine Learning", "Data Science", "HTML", "CSS", "Git", "Linux",
)
CONTACT_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|(?:\+?\d[\d().\s-]{7,}\d)")


class CandidateCollectionError(ValueError):
    pass


def _public_url(value: str) -> tuple[str, str]:
    parsed = urlparse(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise CandidateCollectionError("A public HTTPS profile URL is required.")

    host = parsed.hostname.lower().rstrip(".")
    if host == "linkedin.com" or host.endswith(".linkedin.com"):
        raise CandidateCollectionError("LinkedIn profile scraping is not supported; use an authorized public profile URL.")
    if host == "github.com":
        parts = [part for part in parsed.path.split("/") if part]
        if not parts or parts[0].lower() in {"login", "settings", "features", "orgs", "topics"}:
            raise CandidateCollectionError("The URL is not a public GitHub user profile.")
        return f"https://github.com/{parts[0]}", "github"

    try:
        addresses = {result[4][0] for result in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)}
    except OSError as exc:
        raise CandidateCollectionError("The profile host could not be verified as publicly reachable.") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise CandidateCollectionError("Private and local network profile URLs are not allowed.")
    return value.strip().split("#", 1)[0], "portfolio"


def _redact_contact(value: Optional[str]) -> Optional[str]:
    if not value:
        return value
    return CONTACT_RE.sub("[redacted]", value).strip()


def _skills_from(*values: str) -> list[str]:
    combined = " ".join(value for value in values if value).casefold()
    return [skill for skill in TECH_SKILLS if skill.casefold() in combined]


def _get(url: str, *, headers: Optional[dict[str, str]] = None) -> requests.Response:
    response = requests.get(
        url,
        headers={"User-Agent": USER_AGENT, **(headers or {})},
        timeout=REQUEST_TIMEOUT,
        allow_redirects=False,
    )
    if 300 <= response.status_code < 400:
        raise CandidateCollectionError("Redirects are not followed for safety.")
    response.raise_for_status()
    return response


def _github_candidate(profile_url: str, username: str) -> dict[str, Any]:
    api_base = f"https://api.github.com/users/{username}"
    headers = {"Accept": "application/vnd.github+json"}
    profile_response = _get(api_base, headers=headers)
    profile = profile_response.json()
    repos_response = _get(f"{api_base}/repos?sort=updated&per_page=30", headers=headers)
    repos = repos_response.json()
    if not isinstance(profile, dict) or not isinstance(repos, list):
        raise CandidateCollectionError("GitHub returned an unexpected profile response.")

    projects = []
    readme_text = []
    skills = set()
    for repo in repos:
        if not isinstance(repo, dict) or repo.get("fork"):
            continue
        topics = repo.get("topics") or []
        language = repo.get("language")
        if language:
            skills.add(str(language))
        skills.update(str(topic) for topic in topics)
        projects.append({
            "name": repo.get("name"),
            "description": _redact_contact(repo.get("description")),
            "url": repo.get("html_url"),
            "language": language,
            "topics": topics,
        })
        if len(readme_text) < 10 and repo.get("name") and repo.get("owner", {}).get("login"):
            readme_url = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}/readme"
            try:
                readme_response = _get(readme_url, headers={**headers, "Accept": "application/vnd.github+json"})
                readme = readme_response.json()
                if readme.get("encoding") == "base64":
                    readme_text.append(base64.b64decode(readme.get("content", "")).decode("utf-8", errors="ignore"))
            except (requests.RequestException, CandidateCollectionError, ValueError):
                continue

    bio = _redact_contact(profile.get("bio"))
    clean_readme = _redact_contact(" ".join(readme_text)) or ""
    skills.update(_skills_from(bio or "", clean_readme))
    # Retain only structured profile metadata; do not persist README contents or contact details.
    raw_data = {
        "github_username": username,
        "public_repositories": len(projects),
        "company": _redact_contact(profile.get("company")),
        "blog": profile.get("blog"),
        "account_created_at": profile.get("created_at"),
    }
    return {
        "source_url": profile_url,
        "source": "GitHub",
        "full_name": _redact_contact(profile.get("name")) or username,
        "headline": bio,
        "location": _redact_contact(profile.get("location")),
        "bio": bio,
        "skills": sorted(skills),
        "projects": projects,
        "raw_data": raw_data,
    }


def _person_data(soup: BeautifulSoup) -> dict[str, Any]:
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            parsed = json.loads(script.string or script.get_text())
        except (TypeError, ValueError):
            continue
        objects = parsed if isinstance(parsed, list) else [parsed]
        for item in objects:
            if isinstance(item, dict) and item.get("@type") in {"Person", "ProfilePage"}:
                if item.get("@type") == "ProfilePage" and isinstance(item.get("mainEntity"), dict):
                    return item["mainEntity"]
                return item
    return {}


def _portfolio_candidate(profile_url: str) -> dict[str, Any]:
    parsed = urlparse(profile_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    robots_response = _get(robots_url)
    parser = RobotFileParser()
    parser.set_url(robots_url)
    parser.parse(robots_response.text.splitlines())
    if not parser.can_fetch(USER_AGENT, profile_url):
        raise CandidateCollectionError("The site robots.txt disallows profile collection.")

    response = _get(profile_url)
    soup = BeautifulSoup(response.text, "html.parser")
    person = _person_data(soup)
    title = soup.title.get_text(" ", strip=True) if soup.title else ""

    def meta(*selectors: str) -> Optional[str]:
        for selector in selectors:
            element = soup.select_one(selector)
            if element and element.get("content"):
                return element["content"].strip()
        return None

    description = person.get("description") or meta('meta[name="description"]', 'meta[property="og:description"]')
    name = person.get("name") or meta('meta[property="og:title"]')
    if not name:
        heading = soup.find("h1")
        name = heading.get_text(" ", strip=True) if heading else title
    headline = person.get("jobTitle") or meta('meta[name="occupation"]')
    location = person.get("address")
    if isinstance(location, dict):
        location = ", ".join(str(location[key]) for key in ("addressLocality", "addressRegion", "addressCountry") if location.get(key))
    elif not isinstance(location, str):
        location = None

    text = soup.get_text(" ", strip=True)
    keywords = person.get("knowsAbout", [])
    if isinstance(keywords, str):
        keywords = [keywords]
    meta_keywords = meta('meta[name="keywords"]')
    skills = set(_skills_from(text))
    skills.update(str(value).strip() for value in keywords if str(value).strip())
    if meta_keywords:
        skills.update(value.strip() for value in meta_keywords.split(",") if value.strip())

    if not any((name, headline, description, skills)):
        raise CandidateCollectionError("The page did not contain usable public profile details.")

    bio = _redact_contact(str(description)) if description else None
    return {
        "source_url": profile_url,
        "source": "Portfolio",
        "full_name": _redact_contact(str(name)) if name else None,
        "headline": _redact_contact(str(headline)) if headline else None,
        "location": _redact_contact(str(location)) if location else None,
        "bio": bio,
        "skills": sorted(skills),
        "projects": [],
        "raw_data": {"page_title": _redact_contact(title), "profile_type": person.get("@type", "webpage")},
    }


def collect_profile(profile_url: str) -> dict[str, Any]:
    normalized_url, source = _public_url(profile_url)
    if source == "github":
        username = urlparse(normalized_url).path.strip("/").split("/")[0]
        return _github_candidate(normalized_url, username)
    return _portfolio_candidate(normalized_url)


def _profile_response(profile: CandidateProfile) -> dict[str, Any]:
    return profile.to_dict()


def _save_profile(db: Session, details: dict[str, Any], owner_user_id: int) -> tuple[CandidateProfile, bool]:
    existing = db.query(CandidateProfile).filter(CandidateProfile.source_url == details["source_url"]).first()
    if existing:
        if existing.owner_user_id != owner_user_id:
            raise CandidateCollectionError("This profile URL cannot be attached to this account.")
        return existing, False
    profile = CandidateProfile(
        owner_user_id=owner_user_id,
        source_url=details["source_url"],
        source=details["source"],
        full_name=details["full_name"],
        headline=details["headline"],
        location=details["location"],
        bio=details["bio"],
        skills_json=json.dumps(details["skills"]),
        projects_json=json.dumps(details["projects"]),
        raw_json=json.dumps(details["raw_data"]),
    )
    db.add(profile)
    db.flush()
    return profile, True


def collect_run(run_id: str, profile_urls: list[str]) -> None:
    db = SessionLocal()
    try:
        run = db.query(CandidateCollectionRun).filter(CandidateCollectionRun.run_id == run_id).first()
        if not run:
            return
        run.status = "running"
        db.commit()
        results = []
        collected_count = 0
        failed_count = 0
        seen_urls = set()
        for submitted_url in profile_urls:
            result = {"source_url": submitted_url, "status": "failed", "message": None, "candidate": None}
            try:
                details = collect_profile(submitted_url)
                normalized_url = details["source_url"]
                if normalized_url in seen_urls:
                    result["status"] = "duplicate_in_run"
                    result["message"] = "This profile URL was already processed in this run."
                else:
                    seen_urls.add(normalized_url)
                    profile, created = _save_profile(db, details, run.owner_user_id)
                    result["status"] = "collected" if created else "already_stored"
                    result["candidate"] = _profile_response(profile)
                    if created:
                        collected_count += 1
                db.commit()
            except (CandidateCollectionError, requests.RequestException, ValueError, json.JSONDecodeError) as exc:
                db.rollback()
                result["message"] = str(exc) or "Profile collection failed."
                failed_count += 1
            except Exception:
                db.rollback()
                logger.exception("Unexpected failure collecting candidate profile")
                result["message"] = "Unexpected error while collecting this profile."
                failed_count += 1
            results.append(result)
            run = db.query(CandidateCollectionRun).filter(CandidateCollectionRun.run_id == run_id).first()
            run.results_json = json.dumps(results, default=str)
            run.collected_count = collected_count
            run.failed_count = failed_count
            db.commit()

        run.status = "completed" if failed_count < len(profile_urls) else "failed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Candidate collection run %s failed", run_id)
        run = db.query(CandidateCollectionRun).filter(CandidateCollectionRun.run_id == run_id).first()
        if run:
            run.status = "failed"
            run.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


def create_collection_run(db: Session, profile_urls: list[str], owner_user_id: int) -> CandidateCollectionRun:
    run = CandidateCollectionRun(
        owner_user_id=owner_user_id,
        run_id=f"candidate_{uuid.uuid4().hex}",
        status="queued",
        requested_count=len(profile_urls),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def get_run_response(run: CandidateCollectionRun) -> dict[str, Any]:
    return {
        "run_id": run.run_id,
        "status": run.status,
        "requested_count": run.requested_count,
        "collected_count": run.collected_count,
        "failed_count": run.failed_count,
        "results": run.get_results(),
        "created_at": run.created_at,
        "completed_at": run.completed_at,
    }