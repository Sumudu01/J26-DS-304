import os
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
    GOOGLE_REDIRECT_URI: str = ""

    # LinkedIn OAuth2
    LINKEDIN_CLIENT_ID: str = ""
    LINKEDIN_CLIENT_SECRET: str = ""
    LINKEDIN_REDIRECT_URI: str = ""

    # Frontend URL
    FRONTEND_URL: str = ""

    @field_validator("CORS_ORIGINS", mode="after")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [i.strip() for i in v.split(",") if i.strip()]
        return v

    @field_validator(
        "GOOGLE_REDIRECT_URI",
        "LINKEDIN_REDIRECT_URI",
        "FRONTEND_URL",
        mode="after",
    )
    @classmethod
    def no_empty_urls_in_production(cls, v: str, info) -> str:
        env = os.getenv("ENVIRONMENT", "development")
        if not v and env != "development":
            raise ValueError(
                f"{info.field_name} must be set in production "
                f"(current ENVIRONMENT={env!r})"
            )
        return v

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

