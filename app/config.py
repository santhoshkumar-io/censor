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


settings = Settings()
