"""Cross-Encoder contextual reranking for Component 4.

The final ranking fuses two signals over the FAISS candidate pool:

* the BGE-M3 dense cosine similarity (semantic, multilingual, 8192 tokens), and
* the Cross-Encoder relevance logit (joint query/passage attention, 512 tokens).

``cross-encoder/ms-marco-MiniLM-L-6-v2`` was trained on web-search passages,
so for profile-to-job pairs most of its logits sit in a narrow negative band
and small differences are noise.  Ranking by the Cross-Encoder alone would
throw away the stronger BGE-M3 semantic signal, so both scores are scaled
within the pool (with a minimum spread, see ``_scaled``) and combined with
``dense_weight``.
"""

from __future__ import annotations

import logging
import os
import threading
from collections.abc import Iterable, Mapping, Sequence
from typing import Any, Optional

from app.components.matching.models.embeddings import prepare_job_text

logger = logging.getLogger("emploreralk.components.matching")

CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Weight of the BGE-M3 dense score in the fused ranking; the Cross-Encoder gets
# the remainder.  Override with EMPLORERALK_DENSE_WEIGHT (0.0 - 1.0).
DEFAULT_DENSE_WEIGHT = 0.5
# Smallest score spreads treated as a full-strength difference.  Measured on
# ms-marco-MiniLM for profile/job pairs: clearly relevant jobs sit 5-7 logits
# above the irrelevant band while noise between unrelated jobs stays under
# 0.6 logits; BGE-M3 cosine noise between unrelated jobs is about 0.05.
CROSS_ENCODER_MIN_RANGE = 2.0
DENSE_MIN_RANGE = 0.05
# Lines of the candidate text that are kept out of the Cross-Encoder query.
# The raw CV dump would consume the 512-token budget and truncate the job
# passage; the structured CV sections that carry the same facts are kept.
_RERANK_EXCLUDED_PREFIXES = ("CV parsed text:",)

_cross_encoder_models: dict[tuple[str, Optional[str]], Any] = {}
_cross_encoder_lock = threading.Lock()


def load_cross_encoder(
    *,
    model_name: str = CROSS_ENCODER_MODEL,
    cache_folder: Optional[str] = None,
) -> Any:
    """Load and reuse the true Cross-Encoder from the project model cache.

    Only loads models that were actually trained as cross-encoders (i.e. have
    a trained classification head).  Wrapping a bi-encoder like
    all-MiniLM-L6-v2 as a CrossEncoder produces randomly-initialised
    classification weights and meaningless scores, so that path is intentionally
    NOT attempted here.

    Raises RuntimeError if the model is not in the local project cache; the
    caller (rerank_jobs) then keeps the BGE-M3 dense order.

    local_files_only=True prevents outbound HuggingFace Hub requests.
    """
    import os as _os
    _os.environ["HF_HUB_OFFLINE"] = "1"
    _os.environ["TRANSFORMERS_OFFLINE"] = "1"
    _os.environ["HF_DATASETS_OFFLINE"] = "1"
    _os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    configured_cache = cache_folder or os.getenv("EMPLORERALK_MODEL_CACHE")
    if not configured_cache:
        raise RuntimeError(
            "Set EMPLORERALK_MODEL_CACHE to a model-cache directory "
            "before loading the Cross-Encoder."
        )
    cache_key: tuple[str, str] = (model_name, configured_cache)
    if cache_key in _cross_encoder_models:
        return _cross_encoder_models[cache_key]
    with _cross_encoder_lock:
        if cache_key not in _cross_encoder_models:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as error:
                raise RuntimeError(
                    "Cross-Encoder reranking requires the 'sentence-transformers' package."
                ) from error
            try:
                _cross_encoder_models[cache_key] = CrossEncoder(
                    model_name,
                    cache_folder=configured_cache,
                    device="cpu",
                    local_files_only=True,
                )
            except Exception as error:
                raise RuntimeError(
                    f"Could not load Cross-Encoder model {model_name!r}. "
                    "Check model access, cache location, and runtime compatibility."
                ) from error
            logger.info(
                "Loaded Cross-Encoder %s (float32, cpu, project cache).", model_name
            )
    return _cross_encoder_models[cache_key]


def _retrieved_value(item: Any, name: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(name)
    return getattr(item, name, None)


def _dense_score(item: Any) -> float:
    value = _retrieved_value(item, "similarity_score")
    if value is None:
        value = _retrieved_value(item, "retrieval_similarity_score")
    return float(value or 0.0)


def _scaled(values: Sequence[float], min_range: float) -> list[float]:
    """Scale values to [0, 1] within the pool, dividing by at least ``min_range``.

    Plain min-max would stretch a 0.1-logit Cross-Encoder wobble to the full
    0-1 range and treat it like a decisive 7-logit gap; the floor keeps small
    differences small so neither signal's noise dominates the other.
    """
    low = min(values)
    spread = max(max(values) - low, min_range)
    return [(value - low) / spread for value in values]


def _dense_weight(dense_weight: Optional[float]) -> float:
    if dense_weight is None:
        try:
            dense_weight = float(os.getenv("EMPLORERALK_DENSE_WEIGHT", DEFAULT_DENSE_WEIGHT))
        except ValueError:
            dense_weight = DEFAULT_DENSE_WEIGHT
    if not 0.0 <= dense_weight <= 1.0:
        raise ValueError("dense_weight must be between 0 and 1")
    return dense_weight


def rerank_query(candidate_text: str) -> str:
    """Return the candidate text used as the Cross-Encoder query."""
    lines = [
        line for line in str(candidate_text).splitlines()
        if not line.startswith(_RERANK_EXCLUDED_PREFIXES)
    ]
    return "\n".join(lines) or str(candidate_text)


def rerank_jobs(
    candidate_text: str,
    retrieved_jobs: Iterable[Any],
    *,
    model: Any = None,
    top_k: Optional[int] = None,
    dense_weight: Optional[float] = None,
) -> list[dict[str, Any]]:
    """Rerank dense retrieval results by fusing BGE-M3 and Cross-Encoder scores.

    Encoder resolution order
    ------------------------
    1. ``model`` argument — explicit encoder passed by the caller (tests / overrides).
    2. ``cross-encoder/ms-marco-MiniLM-L-6-v2`` via ``load_cross_encoder()``.
    3. BGE-M3 dense order — when no Cross-Encoder can be loaded.  A weaker
       bi-encoder is deliberately not used here: it would reorder BGE-M3
       results with a less capable semantic model.

    Each result carries ``retrieval_similarity_score`` (BGE-M3 cosine),
    ``cross_encoder_score`` (raw logit, or None without a Cross-Encoder),
    ``final_score`` (the fused score the ranking uses) and ``reranker``.
    """
    if not candidate_text or not str(candidate_text).strip():
        raise ValueError("candidate_text must not be empty")
    if top_k is not None and top_k < 1:
        raise ValueError("top_k must be greater than zero")
    weight = _dense_weight(dense_weight)

    unique: list[Any] = []
    seen_ids: set[Any] = set()
    for item in retrieved_jobs:
        job_id = _retrieved_value(item, "job_id")
        if job_id is None or job_id in seen_ids:
            continue
        seen_ids.add(job_id)
        unique.append(item)
    if not unique:
        return []

    query = rerank_query(candidate_text)
    pairs: list[list[str]] = []
    for item in unique:
        job = _retrieved_value(item, "job")
        if job is None:
            raise ValueError(
                f"retrieved job {_retrieved_value(item, 'job_id')!r} has no job record"
            )
        pairs.append([query, prepare_job_text(job)])

    encoder = model
    if encoder is None:
        try:
            encoder = load_cross_encoder()
        except RuntimeError as error:
            logger.warning(
                "Cross-Encoder unavailable (%s); keeping BGE-M3 dense order.", error
            )

    dense_scores = [_dense_score(item) for item in unique]
    ce_scores: list[Optional[float]] = [None] * len(unique)
    if encoder is None:
        reranker = "none"
        final_scores = dense_scores
    else:
        try:
            raw_scores = encoder.predict(pairs)
            scores = raw_scores.tolist() if hasattr(raw_scores, "tolist") else list(raw_scores)
            if len(scores) != len(unique):
                raise ValueError(
                    "Encoder returned a score count different from the number of jobs"
                )
            ce_scores = [float(score) for score in scores]
        except Exception as error:
            raise RuntimeError("Reranker failed to score the retrieved jobs") from error
        reranker = "cross-encoder"
        final_scores = [
            weight * dense + (1.0 - weight) * ce
            for dense, ce in zip(
                _scaled(dense_scores, DENSE_MIN_RANGE),
                _scaled(ce_scores, CROSS_ENCODER_MIN_RANGE),
            )
        ]

    ranked = sorted(
        zip(unique, dense_scores, ce_scores, final_scores),
        key=lambda row: (row[3], row[1]),
        reverse=True,
    )
    if top_k is not None:
        ranked = ranked[:top_k]
    return [
        {
            "job_id": _retrieved_value(item, "job_id"),
            "rank": rank,
            "retrieval_similarity_score": dense,
            "cross_encoder_score": ce,
            "final_score": float(final),
            "reranker": reranker,
            "job": _retrieved_value(item, "job"),
        }
        for rank, (item, dense, ce, final) in enumerate(ranked, start=1)
    ]
