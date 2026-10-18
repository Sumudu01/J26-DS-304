"""Private CV object storage: Google Drive (default when configured) or local disk.

Storage keys are saved in ``candidate_cvs.storage_key`` in Neon and say where
the file lives, so every backend instance can find the same CV:

* ``gdrive:<file id>`` — a file in the shared ``EmploreraLK-CVs`` Drive folder.
* ``users/<id>/cv/<uuid>.pdf`` — a legacy file on the local disk of the
  machine that received the upload (not visible from other machines).

Google Drive configuration (environment / .env):

* ``CV_STORAGE_BACKEND=gdrive``
* ``CV_GDRIVE_FOLDER_ID`` — the Drive folder that receives CVs.
* Credentials, in order of preference:

  - ``CV_GDRIVE_TOKEN_FILE`` / ``CV_GDRIVE_TOKEN_JSON`` — OAuth refresh token
    of the Google account that owns the files, created once with
    ``python -m app.components.matching.services.gdrive_setup``.  Required for a
    personal Gmail Drive: service accounts have no storage quota there.
  - ``CV_GDRIVE_CREDENTIALS_FILE`` / ``CV_GDRIVE_CREDENTIALS_JSON`` — a
    service-account key; only works with a Shared Drive folder.

  The ``*_JSON`` variants hold the file content for hosts without a file
  system (e.g. Vercel).  Keep every credential file outside the repository.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[4] / ".env")

ALLOWED_CONTENT_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
}
MAX_CV_BYTES = 10 * 1024 * 1024

GDRIVE_PREFIX = "gdrive:"
# OAuth uses drive.file: the app sees only files and folders it created, so a
# leaked token cannot expose the rest of the owner's Drive.
GDRIVE_OAUTH_SCOPES = ("https://www.googleapis.com/auth/drive.file",)
_GDRIVE_SCOPES = ("https://www.googleapis.com/auth/drive",)
_DRIVE_FILES = "https://www.googleapis.com/drive/v3/files"
_DRIVE_UPLOAD = "https://www.googleapis.com/upload/drive/v3/files"
_DRIVE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{10,200}$")
_TIMEOUT_SECONDS = 60


def _safe_suffix(filename: str, content_type: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in {".pdf", ".doc", ".docx"} else ALLOWED_CONTENT_TYPES[content_type]


def _ipv4_session(session_class: Any, credentials: Any) -> Any:
    """Authorized session whose connections (API calls and token refresh) use IPv4.

    On networks with broken IPv6, requests tries each IPv6 address first and
    waits 20-40 s per timeout before falling back; one upload took 192 s.
    Binding the local socket to an IPv4 address skips IPv6 immediately.
    Google's endpoints are always reachable over IPv4.
    """
    import requests
    from google.auth.transport.requests import Request
    from requests.adapters import HTTPAdapter

    class _IPv4Adapter(HTTPAdapter):
        def init_poolmanager(self, *args: Any, **kwargs: Any) -> None:
            kwargs["source_address"] = ("0.0.0.0", 0)
            super().init_poolmanager(*args, **kwargs)

    def mounted(session: Any) -> Any:
        session.mount("https://", _IPv4Adapter())
        return session

    session = session_class(credentials, auth_request=Request(mounted(requests.Session())))
    return mounted(session)


class _GoogleDrive:
    """Minimal Drive v3 client over google-auth (no extra SDK dependency)."""

    def __init__(self) -> None:
        self._session: Any = None
        self._lock = threading.Lock()

    @property
    def folder_id(self) -> str:
        folder_id = (os.getenv("CV_GDRIVE_FOLDER_ID") or "").strip()
        if not folder_id:
            raise RuntimeError("CV_GDRIVE_FOLDER_ID must be set for Google Drive CV storage")
        return folder_id

    def _authorized_session(self) -> Any:
        if self._session is not None:
            return self._session
        with self._lock:
            if self._session is None:
                try:
                    from google.auth.transport.requests import AuthorizedSession
                    from google.oauth2 import credentials as oauth_credentials
                    from google.oauth2 import service_account
                except ImportError as error:
                    raise RuntimeError("Google Drive CV storage requires the google-auth package") from error
                token_json = os.getenv("CV_GDRIVE_TOKEN_JSON")
                token_file = os.getenv("CV_GDRIVE_TOKEN_FILE")
                raw_json = os.getenv("CV_GDRIVE_CREDENTIALS_JSON")
                key_file = os.getenv("CV_GDRIVE_CREDENTIALS_FILE")
                if token_json or (token_file and Path(token_file).is_file()):
                    info = json.loads(token_json or Path(token_file).read_text(encoding="utf-8"))
                    credentials = oauth_credentials.Credentials.from_authorized_user_info(
                        info, scopes=GDRIVE_OAUTH_SCOPES
                    )
                elif raw_json:
                    credentials = service_account.Credentials.from_service_account_info(
                        json.loads(raw_json), scopes=_GDRIVE_SCOPES
                    )
                elif key_file and Path(key_file).is_file():
                    credentials = service_account.Credentials.from_service_account_file(
                        key_file, scopes=_GDRIVE_SCOPES
                    )
                else:
                    raise RuntimeError(
                        "Set CV_GDRIVE_TOKEN_FILE (run gdrive_setup once) or a service-account "
                        "key in CV_GDRIVE_CREDENTIALS_FILE for Google Drive CV storage"
                    )
                self._session = _ipv4_session(AuthorizedSession, credentials)
        return self._session

    @staticmethod
    def _raise_for_status(response: Any, action: str) -> None:
        if response.status_code < 400:
            return
        try:
            error = response.json().get("error", {})
            reason = (error.get("errors") or [{}])[0].get("reason") or error.get("status")
            message = error.get("message") or response.text[:200]
        except ValueError:
            reason, message = None, response.text[:200]
        if response.status_code == 404:
            raise FileNotFoundError(f"Google Drive file not found while trying to {action}")
        if reason == "storageQuotaExceeded":
            raise RuntimeError(
                "Google Drive rejected the upload (storageQuotaExceeded): a service account "
                "cannot store files in a personal My Drive; use the OAuth token "
                "(CV_GDRIVE_TOKEN_FILE) or a Shared Drive folder."
            )
        raise RuntimeError(f"Google Drive could not {action} ({response.status_code} {reason}): {message}")

    def upload(self, name: str, content_type: str, data: bytes, properties: dict[str, str]) -> str:
        boundary = uuid.uuid4().hex
        metadata = {"name": name, "parents": [self.folder_id], "appProperties": properties}
        body = b"".join([
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode(),
            json.dumps(metadata).encode(),
            f"\r\n--{boundary}\r\nContent-Type: {content_type}\r\n\r\n".encode(),
            data,
            f"\r\n--{boundary}--\r\n".encode(),
        ])
        response = self._authorized_session().post(
            _DRIVE_UPLOAD,
            params={"uploadType": "multipart", "supportsAllDrives": "true", "fields": "id"},
            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
            data=body,
            timeout=_TIMEOUT_SECONDS,
        )
        self._raise_for_status(response, "upload the CV")
        return response.json()["id"]

    def download(self, file_id: str) -> bytes:
        response = self._authorized_session().get(
            f"{_DRIVE_FILES}/{file_id}",
            params={"alt": "media", "supportsAllDrives": "true"},
            timeout=_TIMEOUT_SECONDS,
        )
        self._raise_for_status(response, "download the CV")
        return response.content

    def delete(self, file_id: str) -> None:
        response = self._authorized_session().delete(
            f"{_DRIVE_FILES}/{file_id}",
            params={"supportsAllDrives": "true"},
            timeout=_TIMEOUT_SECONDS,
        )
        if response.status_code == 404:
            return
        self._raise_for_status(response, "delete the CV")


class CVObjectStorage:
    """Store private CV files under random, user-scoped keys."""

    def __init__(self, *, backend: Optional[str] = None, root_dir: Optional[str] = None):
        self._backend = backend
        self.root_dir = Path(
            root_dir or os.getenv("CV_STORAGE_DIR", Path(__file__).resolve().parents[3] / "data" / "cv_storage")
        )
        self._drive = _GoogleDrive()

    @property
    def backend(self) -> str:
        # Resolved per call so .env values loaded after import still apply.
        backend = (self._backend or os.getenv("CV_STORAGE_BACKEND", "local")).lower()
        if backend not in {"local", "gdrive"}:
            raise ValueError("CV_STORAGE_BACKEND must be 'gdrive' or 'local'")
        return backend

    @staticmethod
    def validate_upload(filename: str, content_type: str, data: bytes) -> None:
        if content_type not in ALLOWED_CONTENT_TYPES:
            raise ValueError("Only PDF and Word CV files are supported")
        if not filename or Path(filename).suffix.lower() not in {".pdf", ".doc", ".docx"}:
            raise ValueError("The CV filename must end with .pdf, .doc, or .docx")
        if not data:
            raise ValueError("The uploaded CV is empty")
        if len(data) > MAX_CV_BYTES:
            raise ValueError("The CV must be smaller than 10 MB")

    def store(self, user_id: int, filename: str, content_type: str, data: bytes) -> tuple[str, str]:
        self.validate_upload(filename, content_type, data)
        digest = hashlib.sha256(data).hexdigest()
        object_name = f"{uuid.uuid4().hex}{_safe_suffix(filename, content_type)}"
        if self.backend == "gdrive":
            # Drive names carry no personal data; the owner is recorded in Neon.
            file_id = self._drive.upload(
                f"user-{user_id}-{object_name}",
                content_type,
                data,
                {"emploreralk_user_id": str(user_id), "sha256": digest},
            )
            return f"{GDRIVE_PREFIX}{file_id}", digest
        key = f"users/{user_id}/cv/{object_name}"
        destination = self.root_dir / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return key, digest

    def read(self, key: str) -> bytes:
        if key.startswith(GDRIVE_PREFIX):
            return self._drive.download(self._drive_id(key))
        path = self._local_path(key)
        if not path.is_file():
            raise FileNotFoundError("CV object was not found")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        if key.startswith(GDRIVE_PREFIX):
            self._drive.delete(self._drive_id(key))
            return
        path = self._local_path(key)
        if path.is_file():
            path.unlink()

    @staticmethod
    def _drive_id(key: str) -> str:
        file_id = key[len(GDRIVE_PREFIX):]
        if not _DRIVE_ID_RE.match(file_id):
            raise ValueError("Invalid CV storage key")
        return file_id

    def _local_path(self, key: str) -> Path:
        path = Path(key)
        if not key or path.is_absolute() or ".." in path.parts or not key.startswith("users/"):
            raise ValueError("Invalid CV storage key")
        return self.root_dir / key


storage = CVObjectStorage()
