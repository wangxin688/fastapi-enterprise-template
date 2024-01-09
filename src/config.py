import tomllib
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).parent.parent
PYPROJECT_CONTENT = tomllib.load(f"{PROJECT_DIR}/pyproject.toml")["project"]


class Settings(BaseSettings):
    SECRET_KEY: str
    SECRUITY_BCRYPT_ROUNDS: int = 4
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 11520
    BACKEND_CORS_ORIGIN: list[str] = ["*"]
    ALLOWED_HOST: list[str] = ["*"]

    PROJECT_NAME: str = PYPROJECT_CONTENT["name"]
    VERSION: str = PYPROJECT_CONTENT["version"]
    DESCRIPTION: str = PYPROJECT_CONTENT["description"]
    LIMITED_RATE: tuple[int, int] = (20, 10)

    WEB_SENTRY_DSN: str | None = None
    CELERY_SENTRY_DSN: str | None = None
    SENTRY_SAMPLE_RATE: float | None = 1.0
    SENTRY_TRACES_SAMPLE_RATE: float | None = 1.0

    SQLALCHEMY_DATABASE_URI: str
    DATABSE_POOL_SIZE: int | None = 50
    DATABSE_POOL_MAX_OVERFLOW: int | None = 10
    REDIS_DSN: str

    model_config = SettingsConfigDict(env_file=f"{PROJECT_DIR}/.env", case_sensitive=True, extra="allow")


settings = Settings()
