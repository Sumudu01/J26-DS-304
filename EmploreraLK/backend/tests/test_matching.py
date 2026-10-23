"""Component 4 matching tests that run without downloading any model."""

import json

import numpy as np
import pytest

from app.components.matching.models import embeddings
from app.components.matching.models.embeddings import match_skills_semantically, prepare_candidate_text
from app.components.matching.services.pipeline import _add_reasoning, recommend_jobs
from app.components.matching.models.reranking import rerank_jobs, rerank_query
from app.components.matching.models.retrieval import DenseJobIndex, RetrievedJob


class FakeCrossEncoder:
    def __init__(self, scores):
        self.scores = scores
        self.pairs = None

    def predict(self, pairs):
        self.pairs = pairs
        return np.asarray([self.scores[pair[1].splitlines()[0]] for pair in pairs])


class FakeEncoder:
    """Maps known strings to fixed unit vectors; anything else is orthogonal."""

    def __init__(self, table):
        self.table = table

    def encode(self, texts, **_):
        def vec(text):
            v = np.asarray(self.table.get(text.casefold(), [0.0, 0.0, 1.0]), dtype="float32")
            return v / np.linalg.norm(v)
        if isinstance(texts, str):
            return vec(texts)
        return np.stack([vec(t) for t in texts])


def _jobs():
    return [{"id": 1, "title": "Backend Engineer"}, {"id": 2, "title": "Mobile Developer"}]


def test_fusion_keeps_dense_signal_when_cross_encoder_is_near_flat():
    retrieved = [RetrievedJob(1, 0.59, _jobs()[0]), RetrievedJob(2, 0.53, _jobs()[1])]
    # A 0.1-logit Cross-Encoder preference must not override a clear dense lead alone.
    ce = FakeCrossEncoder({"Job title: Backend Engineer": -10.96, "Job title: Mobile Developer": -10.86})
    ranked = rerank_jobs("Target role: Backend developer", retrieved, model=ce)
    assert [r["job_id"] for r in ranked] == [1, 2]
    assert ranked[0]["reranker"] == "cross-encoder"
    assert ranked[0]["cross_encoder_score"] == pytest.approx(-10.96)
    assert ranked[0]["retrieval_similarity_score"] == pytest.approx(0.59)


def test_strong_cross_encoder_signal_can_promote_a_job():
    retrieved = [RetrievedJob(1, 0.55, _jobs()[0]), RetrievedJob(2, 0.54, _jobs()[1])]
    ce = FakeCrossEncoder({"Job title: Backend Engineer": -11.0, "Job title: Mobile Developer": -4.0})
    ranked = rerank_jobs("Target role: Mobile developer", retrieved, model=ce)
    assert [r["job_id"] for r in ranked] == [2, 1]


def test_without_cross_encoder_dense_order_is_kept_and_reported(monkeypatch):
    def unavailable():
        raise RuntimeError("not cached")
    monkeypatch.setattr("app.components.matching.models.reranking.load_cross_encoder", unavailable)
    retrieved = [RetrievedJob(2, 0.4, _jobs()[1]), RetrievedJob(1, 0.6, _jobs()[0])]
    ranked = rerank_jobs("Target role: Backend developer", retrieved)
    assert [r["job_id"] for r in ranked] == [1, 2]
    assert ranked[0]["reranker"] == "none"
    assert ranked[0]["cross_encoder_score"] is None


def test_raw_cv_text_is_kept_out_of_the_cross_encoder_query():
    text = "Target role: Data Analyst\nCV skills: SQL\nCV parsed text: " + "word " * 2000
    query = rerank_query(text)
    assert "CV parsed text" not in query
    assert "CV skills: SQL" in query


def test_cv_sections_reach_candidate_text_and_disable_domain_expansion():
    profile = {"target_role": "Data Analyst", "skills": ["SQL"],
               "cv": {"work_experience": "Built KPI dashboards", "skills": ["Power BI"]}}
    text = prepare_candidate_text(profile)
    assert "CV work experience: Built KPI dashboards" in text
    assert "Domain context" not in text


def test_domain_context_is_not_sent_to_llm_reasoning():
    seen = {}
    def client(prompt):
        seen["prompt"] = prompt
        return {"recommendation": "possible_match"}
    text = prepare_candidate_text({"target_role": "Cybersecurity Analyst", "skills": ["Python"]})
    assert "Domain context" in text
    ranked = [{"job_id": 1, "job": {"title": "SOC Analyst"}}]
    _add_reasoning(text, ranked, llm_client=client, llm_model=None, reasoning_top_k=1)
    assert "SIEM" not in seen["prompt"]
    assert "Target role: Cybersecurity Analyst" in seen["prompt"]


def test_semantic_skill_matching_finds_aliases_and_rejects_neighbours(monkeypatch):
    monkeypatch.setattr(embeddings, "_skill_vectors", {})
    encoder = FakeEncoder({
        "javascript": [1.0, 0.0, 0.0],
        "js": [0.95, 0.31, 0.0],      # cosine 0.95 with JavaScript
        "c++": [0.0, 1.0, 0.0],
        "c#": [0.0, 0.75, 0.66],       # cosine 0.75 with C++: below threshold
    })
    matches = match_skills_semantically(["JavaScript", "C++"], [["JS", "C#", "javascript"]], model=encoder)[0]
    by_job_skill = {m["job_skill"]: m for m in matches}
    assert by_job_skill["JS"]["candidate_skill"] == "JavaScript"
    assert by_job_skill["JS"]["match_type"] == "semantic"
    assert by_job_skill["javascript"]["match_type"] == "exact"
    assert "C#" not in by_job_skill


def test_recommend_jobs_end_to_end_with_fakes():
    jobs = _jobs()
    encoder = FakeEncoder({})
    job_vectors = [[1.0, 0.0, 0.0], [0.6, 0.8, 0.0]]
    index = DenseJobIndex.build(zip(jobs, job_vectors))
    ce = FakeCrossEncoder({"Job title: Backend Engineer": 2.0, "Job title: Mobile Developer": -3.0})

    class QueryEncoder(FakeEncoder):
        def encode(self, texts, **kw):
            return np.asarray([1.0, 0.0, 0.0], dtype="float32")

    results = recommend_jobs({"target_role": "Backend developer"}, job_index=index,
                             embedding_model=QueryEncoder({}), cross_encoder=ce, reasoning_top_k=None)
    assert [r["job_id"] for r in results] == [1, 2]
    assert all("final_score" in r for r in results)


def test_index_vectors_round_trip_for_incremental_rebuild():
    index = DenseJobIndex.build(zip(_jobs(), [[3.0, 4.0, 0.0], [0.0, 0.0, 2.0]]))
    vectors = index.vectors_by_id()
    assert vectors[1] == pytest.approx([0.6, 0.8, 0.0])
    assert vectors[2] == pytest.approx([0.0, 0.0, 1.0])


def test_embed_processed_job_postings_encodes_only_jobs_without_reusable_vectors():
    class Job:
        def __init__(self, job_id):
            self.id, self.title, self.status = job_id, f"Job {job_id}", "processed"
        def get_processed_skills(self):
            return {"canonical_skills": ["Python"]}
        def get_skills(self):
            return []

    class Query:
        def __init__(self, rows): self.rows = rows
        def filter(self, *a): return self
        def order_by(self, *a): return self
        def all(self): return self.rows

    class Session:
        def query(self, *_): return Query([Job(1), Job(2)])
        def rollback(self): pass

    class CountingEncoder(FakeEncoder):
        calls = []
        def encode(self, texts, **kw):
            self.calls.append(list(texts))
            return super().encode(texts, **kw)

    encoder = CountingEncoder({})
    result = embeddings.embed_processed_job_postings(Session(), model=encoder, reuse={1: [1.0, 0.0, 0.0]})
    assert [job.id for job, _ in result] == [1, 2]
    assert result[0][1] == [1.0, 0.0, 0.0]
    assert len(encoder.calls) == 1 and len(encoder.calls[0]) == 1


def test_result_cache_expires(monkeypatch):
    from app.components.matching.services import pipeline
    monkeypatch.setattr(pipeline, "_result_cache", pipeline.OrderedDict())
    pipeline._cache_put(("k",), [1])
    assert pipeline._cache_get(("k",)) == [1]
    monkeypatch.setattr(pipeline.time, "monotonic", lambda: 10**9)
    assert pipeline._cache_get(("k",)) is None


def test_llm_quota_error_pauses_further_calls(monkeypatch):
    from app.components.matching.services import reasoning
    monkeypatch.setattr(reasoning, "_quota_blocked_until", 0.0)
    calls = []
    class Response:
        status_code = 429
    class QuotaError(Exception):
        response = Response()
    def failing_http(*args):
        calls.append(1)
        raise QuotaError("429")
    monkeypatch.setattr(reasoning, "_http_reason", failing_http)
    ranked = [{"job_id": 1, "job": {"title": "A"}}, {"job_id": 2, "job": {"title": "B"}}]
    reasoning.reason_about_matches("cand", ranked, api_key="k")
    reasoning.reason_about_matches("cand", ranked, api_key="k")
    assert len(calls) == 1


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, content=b""):
        self.status_code, self._payload, self.content = status_code, payload or {}, content
        self.text = json.dumps(self._payload)
    def json(self):
        return self._payload


class _FakeDriveSession:
    def __init__(self):
        self.files, self.calls = {}, []
    def post(self, url, params=None, headers=None, data=None, timeout=None):
        self.calls.append(("post", url, params))
        self.files["file123abcde"] = data
        return _FakeResponse(payload={"id": "file123abcde"})
    def get(self, url, params=None, timeout=None):
        file_id = url.rsplit("/", 1)[-1]
        if file_id not in self.files:
            return _FakeResponse(404, {"error": {"message": "not found"}})
        return _FakeResponse(content=b"%PDF-stored")
    def delete(self, url, params=None, timeout=None):
        self.files.pop(url.rsplit("/", 1)[-1], None)
        return _FakeResponse(204)


def test_gdrive_storage_round_trip_without_network(monkeypatch, tmp_path):
    from app.components.matching.services.cv_storage import CVObjectStorage
    monkeypatch.setenv("CV_GDRIVE_FOLDER_ID", "folderIdABC123")
    storage = CVObjectStorage(backend="gdrive", root_dir=str(tmp_path))
    fake = _FakeDriveSession()
    storage._drive._session = fake
    key, digest = storage.store(22, "My CV.pdf", "application/pdf", b"%PDF-1.4 data")
    assert key == "gdrive:file123abcde" and len(digest) == 64
    upload_body = fake.files["file123abcde"]
    assert b'"parents": ["folderIdABC123"]' in upload_body and b"My CV" not in upload_body
    assert storage.read(key) == b"%PDF-stored"
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.read(key)


def test_legacy_local_keys_still_readable_under_gdrive_backend(tmp_path):
    from app.components.matching.services.cv_storage import CVObjectStorage
    legacy = tmp_path / "users" / "22" / "cv" / "old.pdf"
    legacy.parent.mkdir(parents=True)
    legacy.write_bytes(b"%PDF-old")
    storage = CVObjectStorage(backend="gdrive", root_dir=str(tmp_path))
    assert storage.read("users/22/cv/old.pdf") == b"%PDF-old"
    storage.delete("users/22/cv/old.pdf")
    assert not legacy.exists()
    for bad in ("../secret", "gdrive:../../x", "C:/Windows/x"):
        with pytest.raises(ValueError):
            storage.read(bad)


def test_quota_error_is_explained():
    from app.components.matching.services.cv_storage import _GoogleDrive
    response = _FakeResponse(403, {"error": {"errors": [{"reason": "storageQuotaExceeded"}], "message": "quota"}})
    with pytest.raises(RuntimeError, match="OAuth token"):
        _GoogleDrive._raise_for_status(response, "upload the CV")
