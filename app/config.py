from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (the folder that holds pyproject.toml), so the .env file is
# found no matter which directory the server is started from.
ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DB_URL: str

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    # Celery broker; set BROKER_URL in .env to override the local Redis default.
    BROKER_URL: str = "redis://localhost:6379/0"

settings = Settings()
