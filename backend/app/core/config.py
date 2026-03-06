"""
Application configuration management.
"""
import os
from pathlib import Path
from typing import Optional

# Load .env before reading any env vars (ensures CORS_ORIGINS_EXTRA etc. are available)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(_env_path)


class Settings:
    """Application settings loaded from environment variables."""

    # Application
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_DEBUG: bool = os.getenv("APP_DEBUG", "true").lower() == "true"
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./warehouse.db")

    # JWT Authentication
    JWT_SECRET: str = os.getenv(
        "JWT_SECRET", "dev-secret-key-change-in-production-min-32-chars"
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_EXPIRATION_MINUTES: int = int(os.getenv("JWT_EXPIRATION_MINUTES", "1440"))

    # MCP Server (tool calls via MCP when enabled)
    USE_MCP_SERVER: bool = os.getenv("USE_MCP_SERVER", "1") == "1"

    # AWS Integration
    USE_AWS: bool = os.getenv("USE_AWS", "0") == "1"
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    DYNAMO_STATUS_TABLE: str = os.getenv("DYNAMO_STATUS_TABLE", "pipeline_status")
    S3_BUCKET_NAME: str = os.getenv("S3_BUCKET_NAME", "xtern-agents-bucket")
    BEDROCK_MODEL_ID: str = os.getenv(
        "BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"
    )

    # CORS (base + extra from CORS_ORIGINS_EXTRA env, comma-separated)
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ] + [
        o.strip() for o in os.getenv("CORS_ORIGINS_EXTRA", "").split(",") if o.strip()
    ]


settings = Settings()
