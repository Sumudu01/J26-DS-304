from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+psycopg2://neondb_owner:npg_zEGjYTL5V8Js@ep-steep-mountain-b5d7atgm-pooler.c-7.us-east-2.aws.neon.tech/neondb?sslmode=require"
    SECRET_KEY: str = "emploreralk-super-secret-key-change-in-production-2026-sliit"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    HOST: str = "127.0.0.1"
    PORT: int = 5000
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: Union[str, List[str]] = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:5000,*"

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:5000/api/auth/google/callback"

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:5173"

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

