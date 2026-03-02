"""
Application configuration using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # DynamoDB
    DYNAMODB_TABLE_CASES: str = "cases"
    DYNAMODB_ENDPOINT_URL: str | None = None

    # S3
    S3_BUCKET_NAME: str = "xtern-agents-bucket"

    # Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-sonnet-20240229-v1:0"

    # Logging
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
