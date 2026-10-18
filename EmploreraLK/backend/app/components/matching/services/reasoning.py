"""Optional LLM reasoning over Cross-Encoder-ranked job recommendations."""

from __future__ import annotations

import json
import logging
import os
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

logger = logging.getLogger("emploreralk.components.matching")

DEFAULT_LLM_MODEL = "gpt-4o-mini"
DEFAULT_LLM_ENDPOINT = "https://api.openai.com/v1/chat/completions"
# After a 429 (quota exhausted / rate limited) the endpoint is not called again
# for this long, so every request does not pay for a failing round trip.
_QUOTA_COOLDOWN_SECONDS = 600
_quota_blocked_until = 0.0

load_dotenv(Path(__file__).resolve().parents[4] / ".env")


def _value(item: Any, name: str) -> Any:
    if isinstance(item, Mapping):
        return item.get(name)
    return getattr(item, name, None)


def _job_text(job: Any) -> str:
    if isinstance(job, Mapping):
        return "\n".join(
            f"{label}: {job.get(field, '')}"
            for label, field in (
                ("Title", "title"),
                ("Company", "company"),
                ("Location", "location"),
                ("Description", "description_raw"),
            )
            if job.get(field)
        )
    return "\n".join(
        f"{label}: {getattr(job, field, '')}"
        for label, field in (
            ("Title", "title"),
            ("Company", "company"),
            ("Location", "location"),
            ("Description", "description_raw"),
        )
        if getattr(job, field, None)
    )


def _prompt(candidate_text: str, result: Mapping[str, Any]) -> str:
    return (
        "Assess this candidate-job match using only the supplied information. "
        "Return valid JSON with exactly these keys: fit_summary, matching_skills, "
        "skill_gaps, evidence, risks, recommendation. Do not invent facts. "
        "The recommendation must be one of strong_match, possible_match, or weak_match.\n\n"
        f"Candidate context:\n{candidate_text}\n\n"
        f"Job context:\n{_job_text(_value(result, 'job'))}\n\n"
        f"Retrieval similarity score: {_value(result, 'retrieval_similarity_score')}\n"
        f"Cross-Encoder score: {_value(result, 'cross_encoder_score')}"
    )


def _parse_response(content: str) -> dict[str, Any]:
    try:
        value = json.loads(content)
    except (TypeError, ValueError) as error:
        raise ValueError("LLM returned invalid JSON reasoning") from error
    if not isinstance(value, dict):
        raise ValueError("LLM reasoning must be a JSON object")
    return value


def _http_reason(client: Any, endpoint: str, api_key: str, model: str, prompt: str) -> dict[str, Any]:
    response = client.post(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "You are a careful recruitment matching analyst."},
                {"role": "user", "content": prompt},
            ],
        },
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return _parse_response(content)


def _is_quota_error(error: Exception) -> bool:
    """Return True when *error* indicates an OpenAI quota / rate-limit response (HTTP 429)."""
    # httpx raises HTTPStatusError for non-2xx; check status_code attribute
    status_code = getattr(getattr(error, "response", None), "status_code", None)
    if status_code == 429:
        return True
    # Some callers may wrap or re-raise with the status code in the message
    return "429" in str(error)


def reason_about_matches(
    candidate_text: str,
    ranked_jobs: Iterable[Mapping[str, Any]],
    *,
    client: Any = None,
    model: Optional[str] = None,
    endpoint: Optional[str] = None,
    api_key: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Add grounded LLM reasoning after Cross-Encoder ranking when configured.

    429 circuit-breaker
    -------------------
    Once any call to the LLM returns a 429 (rate-limit / quota exhausted) the
    remaining jobs in the batch are immediately skipped with
    ``llm_reasoning=None``.  This prevents up to ``reasoning_top_k × timeout``
    seconds of extra latency (e.g. 3 × 20 s = 60 s) from blocking the whole
    recommendation response when the API key has run out of quota.

    The per-call HTTP timeout is also capped at 8 s (down from 20 s) because
    a 429 response is typically returned quickly; waiting 20 s per failed call
    adds unnecessary latency.
    """
    global _quota_blocked_until
    results = [dict(result) for result in ranked_jobs]
    configured_key = api_key or os.getenv("EMPLORERALK_LLM_API_KEY")
    if not configured_key and client is None:
        return [{**result, "llm_reasoning": None} for result in results]
    if client is None and time.monotonic() < _quota_blocked_until:
        return [{**result, "llm_reasoning": None} for result in results]

    llm_model = model or os.getenv("EMPLORERALK_LLM_MODEL", DEFAULT_LLM_MODEL)
    llm_endpoint = endpoint or os.getenv("EMPLORERALK_LLM_ENDPOINT", DEFAULT_LLM_ENDPOINT)
    # Reduced timeout: 8 s is enough for a healthy API; 429s arrive instantly.
    http_client = client or httpx.Client(timeout=8.0)
    quota_exhausted = False  # circuit-breaker flag
    try:
        for result in results:
            # ── Circuit-breaker: skip remaining calls after a 429 ─────────────
            if quota_exhausted:
                result["llm_reasoning"] = None
                continue

            prompt = _prompt(candidate_text, result)
            try:
                if client is not None and callable(client):
                    reasoning = client(prompt)
                elif client is not None and callable(getattr(client, "reason", None)):
                    reasoning = client.reason(prompt)
                else:
                    reasoning = _http_reason(
                        http_client,
                        llm_endpoint,
                        configured_key or "",
                        llm_model,
                        prompt,
                    )
                if not isinstance(reasoning, Mapping):
                    raise ValueError("LLM reasoning must be a mapping")
                result["llm_reasoning"] = dict(reasoning)
            except Exception as error:
                if _is_quota_error(error):
                    quota_exhausted = True
                    if client is None:
                        _quota_blocked_until = time.monotonic() + _QUOTA_COOLDOWN_SECONDS
                    logger.warning(
                        "OpenAI 429 quota error — skipping LLM reasoning for "
                        "%d s: %s",
                        _QUOTA_COOLDOWN_SECONDS,
                        error,
                    )
                else:
                    logger.warning(
                        "Skipping LLM reasoning for job %s: %s",
                        result.get("job_id"),
                        error,
                    )
                result["llm_reasoning"] = None
    finally:
        if client is None:
            http_client.close()
    return results
