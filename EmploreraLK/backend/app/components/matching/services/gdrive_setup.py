"""One-time Google Drive authorisation for CV storage.

Run from the backend directory:

    python -m app.components.matching.services.gdrive_setup ^
        --client-secret D:\\emploreralk-oauth-client.json ^
        --token-out D:\\emploreralk-gdrive-token.json

It opens the browser so the Drive owner can sign in, stores the refresh token
in ``--token-out`` (keep it outside the repository), creates the app-owned
``EmploreraLK-CVs`` folder, checks upload/download/delete, and prints the
.env lines to add.  Uses only google-auth and the standard library.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import secrets
import sys
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

from app.components.matching.services.cv_storage import GDRIVE_OAUTH_SCOPES

_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_TOKEN_URL = "https://oauth2.googleapis.com/token"
_FOLDER_MIME = "application/vnd.google-apps.folder"


def _client_config(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    config = data.get("installed") or data.get("web")
    if not config or "client_id" not in config:
        raise SystemExit("The client-secret file must be an OAuth client of type 'Desktop app'.")
    return config


def _authorise(config: dict) -> dict:
    """Loopback + PKCE desktop flow; returns Google's token response."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)
    result: dict = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 (http.server API)
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if query.get("state", [""])[0] == state:
                result.update({k: v[0] for k, v in query.items()})
            ok = "code" in result
            self.send_response(200 if ok else 400)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            message = "EmploreraLK can now store CVs in Google Drive. You can close this tab." if ok \
                else "Authorisation failed or was cancelled. Return to the terminal."
            self.wfile.write(f"<html><body><p>{message}</p></body></html>".encode())

        def log_message(self, *args) -> None:
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect_uri = f"http://127.0.0.1:{server.server_port}/"
    url = _AUTH_URL + "?" + urllib.parse.urlencode({
        "client_id": config["client_id"],
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GDRIVE_OAUTH_SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # always return a refresh token
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    print("Opening the browser for Google sign-in. If it does not open, visit:\n" + url + "\n")
    webbrowser.open(url)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()
    thread.join(timeout=600)
    server.server_close()
    if "code" not in result:
        raise SystemExit(f"Authorisation did not complete: {result.get('error', 'timed out')}")

    response = requests.post(_TOKEN_URL, data={
        "code": result["code"],
        "client_id": config["client_id"],
        "client_secret": config.get("client_secret", ""),
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
        "code_verifier": verifier,
    }, timeout=60)
    if response.status_code != 200:
        raise SystemExit(f"Token exchange failed: {response.status_code} {response.text[:300]}")
    tokens = response.json()
    if "refresh_token" not in tokens:
        raise SystemExit("Google returned no refresh token; remove the app's access in your "
                         "Google account settings and run this again.")
    return {
        "type": "authorized_user",
        "client_id": config["client_id"],
        "client_secret": config.get("client_secret", ""),
        "refresh_token": tokens["refresh_token"],
        "token_uri": _TOKEN_URL,
    }


def _write_private(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client-secret", required=True, type=Path, help="OAuth 'Desktop app' client JSON")
    parser.add_argument("--token-out", required=True, type=Path, help="where to save the refresh token")
    parser.add_argument("--folder-name", default="EmploreraLK-CVs")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[6]  # J26-DS-304 (git root)
    for path in (args.client_secret, args.token_out):
        if repo_root in path.resolve().parents:
            raise SystemExit(f"{path} is inside the repository; keep credential files outside {repo_root}.")

    token = _authorise(_client_config(args.client_secret))
    _write_private(args.token_out, token)
    print(f"Refresh token saved to {args.token_out}")

    from google.auth.transport.requests import AuthorizedSession
    from google.oauth2.credentials import Credentials

    session = AuthorizedSession(Credentials.from_authorized_user_info(token, scopes=GDRIVE_OAUTH_SCOPES))
    response = session.post(
        "https://www.googleapis.com/drive/v3/files",
        params={"fields": "id,name"},
        json={"name": args.folder_name, "mimeType": _FOLDER_MIME},
        timeout=60,
    )
    response.raise_for_status()
    folder_id = response.json()["id"]
    print(f"Created Drive folder {args.folder_name!r}: {folder_id}")

    os.environ.update({
        "CV_STORAGE_BACKEND": "gdrive",
        "CV_GDRIVE_FOLDER_ID": folder_id,
        "CV_GDRIVE_TOKEN_FILE": str(args.token_out),
    })
    from app.components.matching.services.cv_storage import CVObjectStorage

    storage = CVObjectStorage(backend="gdrive")
    sample = b"%PDF-1.4\n% EmploreraLK storage self-test\n%%EOF\n"
    key, _ = storage.store(0, "selftest.pdf", "application/pdf", sample)
    if storage.read(key) != sample:
        raise SystemExit("Self-test failed: downloaded content differs from the upload.")
    storage.delete(key)
    print("Self-test passed: upload, download and delete work.\n")
    print("Add these lines to backend/.env:\n")
    print("CV_STORAGE_BACKEND=gdrive")
    print(f"CV_GDRIVE_FOLDER_ID={folder_id}")
    print(f"CV_GDRIVE_TOKEN_FILE={args.token_out}")


if __name__ == "__main__":
    sys.exit(main())
