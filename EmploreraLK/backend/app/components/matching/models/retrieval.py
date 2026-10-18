"""FAISS dense retrieval for processed Component 1 job embeddings."""

from __future__ import annotations

import json
import importlib
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any, Optional


class RetrievedJob:
    """A job returned by dense retrieval before contextual reranking."""

    def __init__(self, job_id: Any, similarity_score: float, job: Any = None):
        self.job_id = job_id
        self.similarity_score = float(similarity_score)
        self.job = job

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "retrieval_similarity_score": self.similarity_score,
            "job": self.job,
        }


class DenseJobIndex:
    """In-memory FAISS inner-product index for normalized BGE-M3 vectors."""

    def __init__(self, index: Any, job_ids: list[Any], jobs: Optional[list[Any]] = None):
        self._index = index
        self._job_ids = list(job_ids)
        self._jobs = list(jobs) if jobs is not None else [None] * len(job_ids)
        if len(self._jobs) != len(self._job_ids):
            raise ValueError("jobs and job_ids must have the same length")

    @staticmethod
    def _faiss() -> Any:
        try:
            return importlib.import_module("faiss")
        except ImportError as error:
            raise RuntimeError(
                "FAISS retrieval requires faiss-cpu or faiss-gpu. "
                "Install it in the project environment on the non-C: drive."
            ) from error

    @staticmethod
    def _numpy() -> Any:
        try:
            import numpy as np
        except ImportError as error:
            raise RuntimeError("FAISS retrieval requires NumPy.") from error
        return np

    @staticmethod
    def _job_id(job: Any) -> Any:
        job_id = getattr(job, "id", None)
        if job_id is None and isinstance(job, dict):
            job_id = job.get("id", job.get("job_id"))
        if job_id is None:
            raise ValueError("every indexed job must have an id or job_id")
        return job_id

    @classmethod
    def build(cls, job_embeddings: Iterable[tuple[Any, Sequence[float]]]) -> "DenseJobIndex":
        """Build an index from processed jobs and their BGE-M3 embeddings."""
        faiss = cls._faiss()
        np = cls._numpy()
        rows: list[Any] = []
        job_ids: list[Any] = []
        jobs: list[Any] = []
        seen_ids: set[Any] = set()
        dimension: Optional[int] = None

        for job, embedding in job_embeddings:
            job_id = cls._job_id(job)
            if job_id in seen_ids:
                continue
            vector = np.asarray(list(embedding), dtype="float32")
            if vector.ndim != 1 or vector.size == 0:
                raise ValueError(f"job {job_id!r} has an invalid embedding shape")
            if dimension is None:
                dimension = int(vector.size)
            elif vector.size != dimension:
                raise ValueError(
                    f"job {job_id!r} embedding dimension {vector.size} does not match "
                    f"the index dimension {dimension}"
                )
            if not np.isfinite(vector).all():
                raise ValueError(f"job {job_id!r} has non-finite embedding values")
            norm = float(np.linalg.norm(vector))
            if norm == 0.0:
                raise ValueError(f"job {job_id!r} has a zero-length embedding")
            rows.append(vector / norm)
            job_ids.append(job_id)
            jobs.append(job)
            seen_ids.add(job_id)

        if not rows:
            raise ValueError("cannot build a job index from an empty dataset")

        matrix = np.vstack(rows).astype("float32", copy=False)
        index = faiss.IndexFlatIP(matrix.shape[1])
        index.add(matrix)
        return cls(index, job_ids, jobs)

    @property
    def dimension(self) -> int:
        return int(self._index.d)

    @property
    def size(self) -> int:
        return len(self._job_ids)

    @property
    def job_ids(self) -> tuple[Any, ...]:
        return tuple(self._job_ids)

    def vectors_by_id(self) -> dict[Any, list[float]]:
        """Return the stored (normalized) vectors so unchanged jobs can be reused."""
        if self.size == 0:
            return {}
        matrix = self._index.reconstruct_n(0, self.size)
        return {job_id: matrix[i].tolist() for i, job_id in enumerate(self._job_ids)}

    def attach_jobs(self, jobs: Iterable[Any]) -> "DenseJobIndex":
        """Attach current job records to a loaded ID mapping for reranking."""
        by_id = {self._job_id(job): job for job in jobs}
        self._jobs = [by_id.get(job_id) for job_id in self._job_ids]
        return self

    def search(self, query_embedding: Sequence[float], top_k: int = 10) -> list[RetrievedJob]:
        """Retrieve unique jobs using cosine similarity via normalized inner product."""
        if top_k < 1:
            raise ValueError("top_k must be greater than zero")
        if self.size == 0:
            return []
        np = self._numpy()
        query = np.asarray(list(query_embedding), dtype="float32")
        if query.ndim != 1 or query.size != self.dimension:
            raise ValueError(
                f"query embedding dimension {query.size} does not match index dimension {self.dimension}"
            )
        if not np.isfinite(query).all():
            raise ValueError("query embedding contains non-finite values")
        norm = float(np.linalg.norm(query))
        if norm == 0.0:
            raise ValueError("query embedding must not be zero-length")

        scores, positions = self._index.search((query / norm).reshape(1, -1), min(top_k, self.size))
        results: list[RetrievedJob] = []
        seen_ids: set[Any] = set()
        for score, position in zip(scores[0], positions[0]):
            if int(position) < 0:
                continue
            job_id = self._job_ids[int(position)]
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            results.append(RetrievedJob(job_id, float(score), self._jobs[int(position)]))
        return results

    def save(self, index_dir: str | Path) -> tuple[Path, Path]:
        """Persist FAISS data and the ID mapping to an explicitly selected directory."""
        directory = Path(index_dir)
        directory.mkdir(parents=True, exist_ok=True)
        index_path = directory / "jobs.faiss"
        mapping_path = directory / "jobs.mapping.json"
        self._faiss().write_index(self._index, str(index_path))
        mapping_path.write_text(
            json.dumps({"job_ids": self._job_ids, "dimension": self.dimension}),
            encoding="utf-8",
        )
        return index_path, mapping_path

    @classmethod
    def load(cls, index_dir: str | Path) -> "DenseJobIndex":
        """Load a persisted index and its ID mapping; job records can be attached by the caller."""
        directory = Path(index_dir)
        index_path = directory / "jobs.faiss"
        mapping_path = directory / "jobs.mapping.json"
        if not index_path.is_file() or not mapping_path.is_file():
            raise FileNotFoundError("persisted FAISS index or job mapping is missing")
        metadata = json.loads(mapping_path.read_text(encoding="utf-8"))
        index = cls._faiss().read_index(str(index_path))
        job_ids = metadata.get("job_ids")
        if not isinstance(job_ids, list) or index.ntotal != len(job_ids):
            raise ValueError("persisted FAISS index and job mapping do not match")
        if int(metadata.get("dimension", index.d)) != int(index.d):
            raise ValueError("persisted FAISS index dimension does not match metadata")
        return cls(index, job_ids)
