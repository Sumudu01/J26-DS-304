"""Candidate/job text preparation and BGE-M3 embeddings for matching."""

import json
import logging
import os
import threading
from collections.abc import Mapping, Sequence
from typing import Any, Optional

logger = logging.getLogger("emploreralk.components.matching")

MODEL_NAME = "BAAI/bge-m3"
DEFAULT_EMBED_MAX_TOKENS = 1024

_model: Any = None
_model_lock = threading.Lock()
# Serialises request-time model inference.  Each torch call already uses all
# CPU cores, so parallel requests only slow each other down.
INFERENCE_LOCK = threading.RLock()


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


def _append_cv_fields(parts: list[str], profile: Any) -> None:
    """Append fields from a parsed CV without requiring a profile schema."""
    cv_data = _first_value(profile, ("cv", "cv_data", "resume", "resume_data"))
    cv_data = _parse_json(cv_data)
    if cv_data is None:
        return

    if isinstance(cv_data, Mapping):
        for label, names in (
            ("CV qualifications", ("qualifications", "summary", "professional_summary")),
            ("CV certifications", ("certifications", "certificates")),
            ("CV education", ("education", "education_history")),
            ("CV skills", ("skills", "technical_skills", "technologies")),
            ("CV projects", ("projects", "project_experience")),
            ("CV work experience", ("work_experience", "experience", "employment_history")),
        ):
            value = _first_value(cv_data, names)
            if label == "CV skills":
                _append_skills(parts, label, value, include_proficiency=True)
            else:
                _append_field(parts, label, value)

        raw_text = _first_value(cv_data, ("text", "raw_text", "content"))
        _append_field(parts, "CV parsed text", raw_text)
    else:
        _append_field(parts, "CV parsed text", cv_data)


def _role_domain_context(target_role: Any) -> str:
    """Return a short domain-context phrase for a target role string.

    ms-marco/FAISS are trained on general passage-retrieval text and score
    based on token overlap.  A candidate who only says "Target role:
    Cybersecurity Analyst" with generic skills like Python and SQL will score
    almost identically to a Software Engineer candidate because the shared
    skills dominate the embedding/reranking signal.

    This mapping adds a concise list of domain keywords that are *expected* for
    the role.  The keywords are kept short (one line) so they do not distort the
    embedding — they fill in what the user would have written if they had a
    richer profile, not fabricated qualifications.

    Only adds context when the candidate has not already supplied equivalent
    information through cv_data, education, or experience fields.
    Returning an empty string means "no expansion needed" (profile already rich).
    """
    if not target_role:
        return ""
    role_lower = str(target_role).lower().strip()

    # Map common role families to their core domain vocabulary.
    # Each tuple: (match fragments, context phrase)
    _ROLE_CONTEXT: list[tuple[tuple[str, ...], str]] = [
        (
            ("cybersecurity", "security analyst", "information security",
             "cyber security", "soc analyst", "penetration tester",
             "ethical hacker", "security engineer"),
            "network security vulnerability assessment penetration testing "
            "SIEM firewall IDS incident response threat detection compliance",
        ),
        (
            ("data analyst", "business analyst", "data analytics",
             "business intelligence", "bi analyst", "bi developer",
             "data reporting"),
            "data analysis SQL Excel Power BI Tableau data visualisation "
            "reporting dashboards business intelligence ETL data pipelines",
        ),
        (
            ("data scientist", "machine learning engineer", "ml engineer",
             "ai engineer", "deep learning", "nlp engineer",
             "computer vision"),
            "machine learning deep learning Python TensorFlow PyTorch "
            "statistical modelling feature engineering model deployment MLOps",
        ),
        (
            ("data engineer", "big data", "etl developer",
             "pipeline engineer"),
            "data pipelines ETL Apache Spark Hadoop Kafka AWS data lake "
            "SQL Python data warehousing cloud infrastructure",
        ),
        (
            ("software engineer", "software developer", "backend developer",
             "backend engineer", "backend",),
            "software development REST APIs databases backend architecture "
            "system design version control testing CI/CD",
        ),
        (
            ("full stack", "fullstack", "web developer", "frontend developer",
             "frontend engineer"),
            "full stack web development React Node.js JavaScript REST APIs "
            "databases CSS HTML frontend backend deployment",
        ),
        (
            ("devops", "site reliability", "sre", "platform engineer",
             "cloud engineer", "infrastructure engineer"),
            "DevOps CI/CD Docker Kubernetes cloud AWS Azure Linux "
            "infrastructure automation monitoring deployment",
        ),
        (
            ("database administrator", "dba", "database engineer"),
            "database administration SQL Server PostgreSQL MySQL Oracle "
            "performance tuning backup recovery replication",
        ),
        (
            ("mobile developer", "android developer", "ios developer",
             "flutter developer", "react native"),
            "mobile application development Android iOS Flutter React Native "
            "Swift Kotlin REST APIs mobile UI performance",
        ),
        (
            ("qa engineer", "quality assurance", "test engineer",
             "automation engineer", "sdet"),
            "software testing quality assurance automated testing Selenium "
            "test plans bug tracking CI/CD regression performance testing",
        ),
        (
            ("project manager", "scrum master", "product manager",
             "product owner", "programme manager"),
            "project management Agile Scrum stakeholder management roadmap "
            "sprint planning risk management delivery leadership",
        ),
        (
            ("network engineer", "network administrator", "systems administrator",
             "sysadmin", "it support"),
            "network administration TCP/IP routing switching firewalls "
            "Windows Server Linux Active Directory IT infrastructure support",
        ),
    ]

    for fragments, context in _ROLE_CONTEXT:
        if any(frag in role_lower for frag in fragments):
            return context
    return ""


def prepare_candidate_text(candidate_profile: Any) -> str:
    """Prepare job-relevance text from an existing profile or User-like object.

    If the candidate has a ``target_role`` set and the profile is otherwise
    sparse (no CV, no education, no experience fields), a short domain-context
    phrase is appended so that FAISS retrieval and Cross-Encoder reranking can
    distinguish between roles that share generic skills (e.g. a Cybersecurity
    Analyst and a Software Engineer who both know Python and SQL).

    The expansion is additive-only — it never overwrites existing fields and
    is skipped when the profile already contains rich context from a CV or
    extended fields.
    """
    if candidate_profile is None:
        raise ValueError("candidate_profile must not be empty")

    parts: list[str] = []
    fields = (
        ("Highest education", ("highest_education", "education_level")),
        ("Field of study / IT background", ("field_of_study", "it_background")),
        ("Current employment status", ("current_employment_status", "employment_status")),
        ("Current role", ("current_role",)),
        ("Previous IT experience", ("previous_it_experience", "it_experience")),
        ("Target role", ("target_role", "preferred_it_job_roles", "preferred_roles")),
        ("Primary career goal", ("primary_career_goal", "career_goal")),
        ("University / institute", ("university", "institute")),
        ("Skill-acquisition method", ("skill_acquisition_method",)),
    )
    for label, names in fields:
        value = _first_value(candidate_profile, names)
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

    _append_cv_fields(parts, candidate_profile)

    # ── Target-role domain expansion ──────────────────────────────────────────
    # When the candidate profile is sparse (typical for new users who have only
    # set target_role and a handful of skills), FAISS and the Cross-Encoder
    # receive almost identical query text for every role because "Python SQL Git"
    # dominates all role signals.  Appending a concise domain-context phrase
    # makes the embedding and reranking role-specific without fabricating data.
    #
    # The expansion is suppressed when the profile is already rich (has CV data,
    # education, or previous experience fields) because those provide sufficient
    # domain signal on their own.
    _rich_fields = ("highest_education", "education_level", "field_of_study",
                    "previous_it_experience", "it_experience", "primary_career_goal")
    profile_is_sparse = not any(
        _first_value(candidate_profile, (f,)) for f in _rich_fields
    )
    # Also check: CV data already provides rich context
    has_cv = bool(_first_value(candidate_profile, ("cv", "cv_data", "resume", "resume_data")))
    if profile_is_sparse and not has_cv:
        target_role = _first_value(
            candidate_profile, ("target_role", "preferred_it_job_roles", "preferred_roles")
        )
        domain_ctx = _role_domain_context(target_role)
        if domain_ctx:
            parts.append(f"Domain context for target role: {domain_ctx}")

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
        skills.extend(_skill_items(processed.get("implied_skills")))
        skills.extend(_skill_items(processed.get("core_skills")))
        for item in processed.get("normalized_items", []):
            if isinstance(item, Mapping):
                skills.extend(
                    _skill_items(
                        _first_value(item, ("canonical_name", "normalized_skill", "skill"))
                    )
                )
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

    processed = _get_value(job_posting, "skills_processed")
    if callable(getattr(job_posting, "get_processed_skills", None)):
        processed = job_posting.get_processed_skills()
    if isinstance(processed, Mapping):
        _append_field(parts, "Normalized skill summary", processed.get("summary"))

    if not parts:
        raise ValueError("job_posting contains no supported job-relevance fields")
    return "\n".join(parts)


def embedding_max_tokens() -> int:
    """Token cap for BGE-M3 inputs (EMPLORERALK_EMBED_MAX_TOKENS).

    BGE-M3 accepts 8192 tokens, but CPU attention cost grows with the square
    of the length: a CV-sized profile took minutes per request at 8192.
    Candidate and job texts put their most informative fields first, so the
    cap mostly trims the raw CV dump and the tail of long descriptions.
    """
    try:
        value = int(os.getenv("EMPLORERALK_EMBED_MAX_TOKENS", DEFAULT_EMBED_MAX_TOKENS))
    except ValueError:
        value = DEFAULT_EMBED_MAX_TOKENS
    return max(64, min(value, 8192))


def embedding_config() -> dict[str, Any]:
    """Settings that change job vectors; a persisted index is reused only if they match."""
    return {"model": MODEL_NAME, "max_seq_length": embedding_max_tokens()}


def load_embedding_model(
    *,
    model_name: str = MODEL_NAME,
    cache_folder: Optional[str] = None,
) -> Any:
    """Load one shared SentenceTransformer model safely across threads.

    BGE-M3 is loaded in float32 on CPU.  torch.float16 is NOT used because
    x86 CPUs lack native float16 arithmetic — PyTorch silently falls back to
    float32 arithmetic while still storing weights in float16, which means
    every operation requires an upcasting round-trip and causes model loading
    to take 200-300 s on a 2.3 GB checkpoint.  float32 loads cleanly in
    ~20 s from the local cache and produces identical embedding quality.

    local_files_only=True prevents SentenceTransformer from making any
    outbound HuggingFace Hub request (authentication warnings, DNS latency,
    redirect overhead) when the model is already cached.
    """
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is None:
            import os as _os
            # Force HuggingFace Hub into fully-offline mode before any import.
            # Without these, sentence_transformers still makes outbound DNS /
            # auth requests even when local_files_only=True is set, adding
            # 30-60 s to the load time on Windows machines without a direct
            # internet route to huggingface.co.
            _os.environ["HF_HUB_OFFLINE"] = "1"
            _os.environ["TRANSFORMERS_OFFLINE"] = "1"
            _os.environ["HF_DATASETS_OFFLINE"] = "1"
            _os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as error:
                raise RuntimeError(
                    "BGE-M3 embeddings require the 'sentence-transformers' package. "
                    "Run: pip install sentence-transformers"
                ) from error

            configured_cache = cache_folder or os.getenv("EMPLORERALK_MODEL_CACHE")
            if not configured_cache:
                raise RuntimeError(
                    "Set EMPLORERALK_MODEL_CACHE in your .env file to a model-cache "
                    "directory before loading BGE-M3. "
                    "Example: EMPLORERALK_MODEL_CACHE=D:\\pp1_research\\J26-DS-304\\EmploreraLK\\backend\\.model_cache"
                )
            try:
                # Load in float32 from the local cache only.
                # local_files_only=True + HF_HUB_OFFLINE=1 together ensure
                # zero network activity during the load, bringing cold-start
                # time from ~46 s down to ~14 s on this machine.
                model = SentenceTransformer(
                    model_name,
                    cache_folder=configured_cache,
                    device="cpu",
                    local_files_only=True,
                )
                model.max_seq_length = embedding_max_tokens()
                _model = model
                logger.info(
                    "Loaded BGE-M3 model %s (float32, cpu, local cache, max %d tokens)",
                    model_name,
                    model.max_seq_length,
                )
            except Exception as error:
                raise RuntimeError(
                    f"Could not load embedding model {model_name!r}. "
                    "Check model access, cache location, and runtime compatibility."
                ) from error
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


def generate_embeddings(
    texts: Sequence[str],
    model: Any = None,
    *,
    batch_size: int = 16,
) -> list[list[float]]:
    """Generate normalized embeddings in batches to avoid one model call per job."""
    clean_texts = [_clean_text(text) for text in texts]
    if not clean_texts or any(not text for text in clean_texts):
        raise ValueError("texts must contain only non-empty values")
    if batch_size < 1:
        raise ValueError("batch_size must be greater than zero")
    encoder = model or load_embedding_model()
    try:
        vectors = encoder.encode(
            clean_texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            batch_size=batch_size,
        )
        values = vectors.tolist() if hasattr(vectors, "tolist") else vectors
        if not isinstance(values, Sequence) or len(values) != len(clean_texts):
            raise TypeError("encoder returned an unexpected batch shape")
        results = []
        for vector in values:
            if not isinstance(vector, Sequence) or not vector:
                raise TypeError("encoder returned an invalid vector")
            results.append([float(value) for value in vector])
        return results
    except Exception as error:
        raise RuntimeError("BGE-M3 failed to encode the supplied text batch") from error


# BGE-M3 cosine above which two short skill names are treated as the same
# skill.  Measured on this model: aliases and close equivalents (React/React.js,
# JS/JavaScript, REST APIs/RESTful services) score 0.81-0.91 while distinct
# technologies reach 0.75 (C++/C#, AWS/Azure), so the cut-off favours precision.
SEMANTIC_SKILL_THRESHOLD = 0.80
_SKILL_CACHE_LIMIT = 20000
_skill_vectors: dict[str, list[float]] = {}
_skill_vectors_lock = threading.Lock()


def _skill_embeddings(skills: Sequence[str], model: Any = None) -> dict[str, list[float]]:
    """Return cached normalized embeddings for short skill names.

    The cache is keyed case-insensitively, but the original spelling is what
    gets embedded: lower-casing changes BGE-M3's input ("JS" vs "js").
    """
    spellings: dict[str, str] = {}
    for skill in skills:
        text = _clean_text(skill)
        if text:
            spellings.setdefault(text.casefold(), text)
    keys = list(spellings)
    with _skill_vectors_lock:
        missing = [key for key in keys if key not in _skill_vectors]
    if missing:
        with INFERENCE_LOCK:
            vectors = generate_embeddings([spellings[key] for key in missing], model=model, batch_size=64)
        with _skill_vectors_lock:
            if len(_skill_vectors) + len(missing) > _SKILL_CACHE_LIMIT:
                _skill_vectors.clear()
            _skill_vectors.update(zip(missing, vectors))
    with _skill_vectors_lock:
        return {key: _skill_vectors[key] for key in keys if key in _skill_vectors}


def match_skills_semantically(
    candidate_skills: Sequence[str],
    job_skill_lists: Sequence[Sequence[str]],
    *,
    model: Any = None,
    threshold: float = SEMANTIC_SKILL_THRESHOLD,
) -> list[list[dict[str, Any]]]:
    """Pair each job skill with the closest candidate skill by meaning.

    Returns one list per job; each entry has ``job_skill``, ``candidate_skill``,
    ``similarity`` and ``match_type`` ("exact" or "semantic").  Exact
    (case-insensitive) matches are kept without calling the model.
    """
    candidates = list(dict.fromkeys(_clean_text(s) for s in candidate_skills if _clean_text(s)))
    if not candidates:
        return [[] for _ in job_skill_lists]
    import numpy as np

    by_key = {skill.casefold(): skill for skill in candidates}
    all_job_skills = [skill for skills in job_skill_lists for skill in skills]
    vectors = _skill_embeddings(candidates + all_job_skills, model=model)
    embedded_candidates = [c for c in candidates if c.casefold() in vectors]
    candidate_matrix = (
        np.asarray([vectors[c.casefold()] for c in embedded_candidates], dtype="float32")
        if embedded_candidates else None
    )

    results: list[list[dict[str, Any]]] = []
    for skills in job_skill_lists:
        matches: list[dict[str, Any]] = []
        for job_skill in dict.fromkeys(_clean_text(s) for s in skills if _clean_text(s)):
            key = job_skill.casefold()
            if key in by_key:
                matches.append({
                    "job_skill": job_skill,
                    "candidate_skill": by_key[key],
                    "similarity": 1.0,
                    "match_type": "exact",
                })
                continue
            job_vector = vectors.get(key)
            if job_vector is None or candidate_matrix is None:
                continue
            scores = candidate_matrix @ np.asarray(job_vector, dtype="float32")
            best = int(scores.argmax())
            if float(scores[best]) >= threshold:
                matches.append({
                    "job_skill": job_skill,
                    "candidate_skill": embedded_candidates[best],
                    "similarity": round(float(scores[best]), 4),
                    "match_type": "semantic",
                })
        results.append(matches)
    return results


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
    reuse: Optional[Mapping[Any, Sequence[float]]] = None,
) -> list[tuple[Any, list[float]]]:
    """Embed processed JobPosting records from the forecasting database pipeline.

    ``reuse`` maps job IDs to vectors that are still valid (job unchanged and
    same embedding settings); only the remaining jobs are sent to BGE-M3.
    """
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

    job_postings = query.all()
    eligible_jobs = []
    texts = []
    for job_posting in job_postings:
        processed = job_posting.get_processed_skills()
        has_normalized = bool(
            processed.get("canonical_skills") or processed.get("normalized_items")
        )
        if not has_normalized:
            # The skill-processing agent ran but produced no normalized output
            # (e.g. the job description contained no recognisable skill tokens).
            # The job may still carry useful signal in its title, raw description,
            # and extracted-skills list.  Attempt to build a job text from those
            # fields; only skip if prepare_job_text() cannot produce anything.
            try:
                fallback_text = prepare_job_text(job_posting)
                if not fallback_text.strip():
                    raise ValueError("empty text")
            except Exception as skip_reason:
                logger.warning(
                    "Skipping processed JobPosting %s: no normalized skills and "
                    "fallback text is also empty (%s)",
                    job_posting.id,
                    skip_reason,
                )
                continue
            logger.info(
                "JobPosting %s has no normalized skills but has usable fallback "
                "text (%d chars) — including in index.",
                job_posting.id,
                len(fallback_text),
            )
            eligible_jobs.append(job_posting)
            texts.append(fallback_text)
            continue
        eligible_jobs.append(job_posting)
        texts.append(prepare_job_text(job_posting))

    if callable(getattr(db, "rollback", None)):
        try:
            db.rollback()
        except Exception as error:
            logger.warning(
                "Could not release DB connection before job batch embedding: %s",
                error,
            )

    reuse = reuse or {}
    pending = [i for i, job in enumerate(eligible_jobs) if job.id not in reuse]
    if len(pending) < len(eligible_jobs):
        logger.info(
            "Reusing %d stored job vectors; embedding %d new or changed jobs.",
            len(eligible_jobs) - len(pending),
            len(pending),
        )
    fresh = generate_embeddings([texts[i] for i in pending], model=model) if pending else []
    vectors: list[list[float]] = [list(reuse[job.id]) if job.id in reuse else [] for job in eligible_jobs]
    for i, vector in zip(pending, fresh):
        vectors[i] = vector
    return list(zip(eligible_jobs, vectors))