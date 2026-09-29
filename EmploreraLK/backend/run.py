"""
run.py — Convenience entrypoint to start the EmploreraLK API server.

Usage:
    python run.py

Or with the venv's uvicorn directly:
    uvicorn app.main:app --host 127.0.0.1 --port 5000 --reload
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.ENVIRONMENT == "development"),
        log_level="info",
    )

