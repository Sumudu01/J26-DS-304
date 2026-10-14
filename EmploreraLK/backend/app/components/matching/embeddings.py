"""Candidate/job text preparation and BGE-M3 embeddings for matching."""

import json
import logging
import os
import threading
from collections.abc import Mapping, Sequence
from typing import Any, Optional

logger = logging.getLogger("emploreralk.components.matching")

MODEL_NAME = "BAAI/bge-m3"

_model: Any = None
_model_lock = threading.Lock()


def _get_value(source: Any, name: str) -> Any:
    if isinstance(source, Mapping):
        return source.get(name)
    return getattr(source, name, None)


def _first_value(source: Any, names: Sequence[str]) -> Any:
    for name in names:
        value = _get_value(source, name)
        if value is not None and value != "":
            return value
    return None


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _parse_json(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return value


def _skill_items(value: Any, *, include_proficiency: bool = False) -> list[str]:
    """Normalize skill values and discard explicit proficiency level 0."""
    value = _parse_json(value)
    if value is None:
        return []
    if isinstance(value, str):
        skill = _clean_text(value)
        return [skill] if skill else []
    if isinstance(value, Mapping):
        items: list[str] = []
        for name, details in value.items():
            proficiency = details
            if isinstance(details, Mapping):
                proficiency = _first_value(details, ("proficiency", "level", "rating", "score"))
            if proficiency is not None:
                try:
                    if int(proficiency) == 0:
                        continue
                except (TypeError, ValueError):
                    pass
            skill = _clean_text(name)
            if skill:
                if include_proficiency and proficiency is not None:
                    items.append(f"{skill} (proficiency {proficiency}/3)")
                else:
                    items.append(skill)
        return items
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        items = []
        for entry in value:
            if isinstance(entry, Mapping):
                name = _first_value(entry, ("name", "skill", "title", "value"))
                proficiency = _first_value(entry, ("proficiency", "level", "rating", "score"))
                if proficiency is not None:
                    try:
                        if int(proficiency) == 0:
                            continue
                    except (TypeError, ValueError):
                        pass
                skill = _clean_text(name)
                if skill:
                    if include_proficiency and proficiency is not None:
                        items.append(f"{skill} (proficiency {proficiency}/3)")
                    else:
                        items.append(skill)
            else:
                items.extend(_skill_items(entry, include_proficiency=include_proficiency))
        return items
    skill = _clean_text(value)
    return [skill] if skill else []


def _append_field(parts: list[str], label: str, value: Any) -> None:
    value_text = _clean_text(value)
    if value_text:
        parts.append(f"{label}: {value_text}")


def _append_skills(
    parts: list[str],
    label: str,
    value: Any,
    *,
    include_proficiency: bool = False,
) -> None:
    skills = list(dict.fromkeys(_skill_items(value, include_proficiency=include_proficiency)))
    if skills:
        parts.append(f"{label}: {', '.join(skills)}")


def _cv_value(profile: Any, name: str) -> Any:
    cv_data = _first_value(profile, ("cv", "cv_data", "resume", "resume_data"))
    if cv_data is None:
        return None
    return _get_value(cv_data, name)


def prepare_candidate_text(candidate_profile: Any) -> str:
    """Prepare job-relevance text from an existing profile or User-like object."""
    if candidate_profile is None:
        raise ValueError("candidate_profile must not be empty")

    parts: list[str] = []
    fields = (
        ("Highest education", ("highest_education", "education_level")),
        ("Field of study / IT background", ("field_of_study", "it_background")),
        ("Current employment status", ("current_employment_status", "employment_status")),
        ("Previous IT experience", ("previous_it_experience", "it_experience", "current_role")),
        ("Preferred IT job roles", ("preferred_it_job_roles", "preferred_roles", "target_role")),
        ("Primary career goal", ("primary_career_goal", "career_goal")),
        ("University / institute", ("university", "institute")),
        ("Skill-acquisition method", ("skill_acquisition_method",)),
    )
    for label, names in fields:
        value = _first_value(candidate_profile, names)
        if label == "Preferred IT job roles":
            _append_skills(parts, label, value)
        else:
            _append_field(parts, label, value)

    _append_skills(
        parts,
        "Technical skills",
        _first_value(candidate_profile, ("technical_skills", "skills")),
        include_proficiency=True,
    )
    _append_skills(
        parts,
        "Additional technical skills",
        _first_value(candidate_profile, ("additional_technical_skills",)),
    )

    for label, name in (
        ("CV qualifications", "qualifications"),
        ("CV certifications", "certifications"),
        ("CV education", "education"),
        ("CV skills", "skills"),
        ("CV projects", "projects"),
        ("CV work experience", "work_experience"),
    ):
        _append_field(parts, label, _cv_value(candidate_profile, name))

    if not parts:
        raise ValueError("candidate_profile contains no supported job-relevance fields")
    return "\n".join(parts)


def _job_skills(job_posting: Any) -> list[str]:
    get_skills = getattr(job_posting, "get_skills", None)
    extracted = get_skills() if callable(get_skills) else _get_value(job_posting, "skills_extracted")
    skills = _skill_items(extracted)

    get_processed_skills = getattr(job_posting, "get_processed_skills", None)
    processed = (
        get_processed_skills()
        if callable(get_processed_skills)
        else _parse_json(_get_value(job_posting, "skills_processed"))
    )
    if isinstance(processed, Mapping):
        skills.extend(_skill_items(processed.get("canonical_skills")))
        for item in processed.get("normalized_items", []):
            if isinstance(item, Mapping):
                skills.extend(_skill_items(item.get("canonical_name")))
    return list(dict.fromkeys(skill for skill in skills if skill))


def prepare_job_text(job_posting: Any) -> str:
    """Prepare job-relevance text from an existing JobPosting-like object."""
    if job_posting is None:
        raise ValueError("job_posting must not be empty")

    parts: list[str] = []
    for label, name in (
        ("Job title", "title"),
        ("Location", "location"),
        ("Description", "description_raw"),
        ("Seniority", "seniority_level"),
        ("Minimum experience years", "experience_years_min"),
        ("Education requirement", "education_level"),
    ):
        _append_field(parts, label, _get_value(job_posting, name))
    _append_skills(parts, "Required skills", _job_skills(job_posting))

    if not parts:
        raise ValueError("job_posting contains no supported job-relevance fields")
    return "\n".join(parts)


def load_embedding_model(
    *,
    model_name: str = MODEL_NAME,
    cache_folder: Optional[str] = None,
) -> Any:
    """Load one shared SentenceTransformer model safely across threads."""
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "BGE-M3 embeddings require the 'sentence-transformers' package."
                ) from error
            configured_cache = cache_folder or os.getenv("EMPLORERALK_MODEL_CACHE")
            try:
                _model = SentenceTransformer(model_name, cache_folder=configured_cache)
            except Exception as error:
                raise RuntimeError(
                    f"Could not load embedding model {model_name!r}. "
                    "Check model access, cache location, and runtime compatibility."
                ) from error
            logger.info("Loaded embedding model %s", model_name)
    return _model


def generate_embedding(text: str, model: Any = None) -> list[float]:
    """Generate one normalized embedding from non-empty text."""
    clean_text = _clean_text(text)
    if not clean_text:
        raise ValueError("text must not be empty")
    encoder = model or load_embedding_model()
    try:
        vector = encoder.encode(
            clean_text,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        values = vector.tolist() if hasattr(vector, "tolist") else vector
        if not isinstance(values, Sequence) or isinstance(values, (str, bytes, bytearray)):
            raise TypeError("encoder returned a non-sequence vector")
        result = [float(value) for value in values]
        if not result:
            raise ValueError("encoder returned an empty vector")
        return result
    except Exception as error:
        raise RuntimeError("BGE-M3 failed to encode the supplied text") from error


def embed_candidate(candidate_profile: Any, model: Any = None) -> list[float]:
    """Prepare and embed an existing candidate profile."""
    return generate_embedding(prepare_candidate_text(candidate_profile), model=model)


def embed_candidate_from_db(
    db: Any,
    *,
    candidate_id: Optional[int] = None,
    email: Optional[str] = None,
    model: Any = None,
) -> tuple[Any, list[float]]:
    """Load one seeker from the database and return it with its embedding."""
    if db is None or not callable(getattr(db, "query", None)):
        raise ValueError("db must be an active SQLAlchemy session")
    if candidate_id is None and not email:
        raise ValueError("candidate_id or email must be provided")

    from app.models.user import User

    query = db.query(User).filter(User.role == "seeker")
    if candidate_id is not None:
        query = query.filter(User.id == candidate_id)
    else:
        query = query.filter(User.email == email)
    candidate = query.first()
    if candidate is None:
        raise LookupError("candidate was not found")
    return candidate, embed_candidate(candidate, model=model)


def embed_candidates_from_db(
    db: Any,
    *,
    limit: Optional[int] = None,
    model: Any = None,
) -> list[tuple[Any, list[float]]]:
    """Load seeker profiles from the database and return them with embeddings."""
    if db is None or not callable(getattr(db, "query", None)):
        raise ValueError("db must be an active SQLAlchemy session")
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    from app.models.user import User

    query = db.query(User).filter(User.role == "seeker").order_by(User.id)
    if limit is not None:
        query = query.limit(limit)

    return [(candidate, embed_candidate(candidate, model=model)) for candidate in query.all()]


def embed_job(job_posting: Any, model: Any = None) -> list[float]:
    """Prepare and embed an existing JobPosting record."""
    return generate_embedding(prepare_job_text(job_posting), model=model)


def embed_job_posting(job_posting: Any, model: Any = None) -> list[float]:
    """Embed a JobPosting after forecasting NLP and skill processing complete."""
    if job_posting is None:
        raise ValueError("job_posting must not be empty")

    status = _get_value(job_posting, "status")
    if status is not None and str(status).lower() != "processed":
        raise ValueError("job_posting must have status 'processed' before embedding")

    get_processed_skills = getattr(job_posting, "get_processed_skills", None)
    processed = (
        get_processed_skills()
        if callable(get_processed_skills)
        else _parse_json(_get_value(job_posting, "skills_processed"))
    )
    if not isinstance(processed, Mapping):
        raise ValueError("job_posting has no processed skill data")
    if not processed.get("canonical_skills") and not processed.get("normalized_items"):
        raise ValueError("job_posting has no normalized skills after skill processing")

    return embed_job(job_posting, model=model)


def embed_processed_job_postings(
    db: Any,
    *,
    limit: Optional[int] = None,
    model: Any = None,
) -> list[tuple[Any, list[float]]]:
    """Embed processed JobPosting records from the forecasting database pipeline."""
    if db is None or not callable(getattr(db, "query", None)):
        raise ValueError("db must be an active SQLAlchemy session")
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than zero")

    from app.models.job_posting import JobPosting

    query = (
        db.query(JobPosting)
        .filter(
            JobPosting.status == "processed",
            JobPosting.skills_processed.isnot(None),
        )
        .order_by(JobPosting.id)
    )
    if limit is not None:
        query = query.limit(limit)

    embeddings: list[tuple[Any, list[float]]] = []
    for job_posting in query.all():
        processed = job_posting.get_processed_skills()
        if not processed.get("canonical_skills") and not processed.get("normalized_items"):
            logger.warning(
                "Skipping processed JobPosting %s without normalized skills",
                job_posting.id,
            )
            continue
        embeddings.append((job_posting, embed_job_posting(job_posting, model=model)))
    return embeddings