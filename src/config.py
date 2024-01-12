import tomllib
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.enums import Env

PROJECT_DIR = Path(__file__).parent.parent
with Path.open(f"{PROJECT_DIR}/pyproject.toml", "rb") as f:
    PYPROJECT_CONTENT = tomllib.load(f)["project"]


class Settings(BaseSettings):
    SECRET_KEY: str
    SECURITY_BCRYPT_ROUNDS: int = 4
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 11520
    BACKEND_CORS: list[str] = Field(default=["*"])
    ALLOWED_HOST: list[str] = Field(default=["*"])

    PROJECT_NAME: str = PYPROJECT_CONTENT["name"]
    VERSION: str = PYPROJECT_CONTENT["version"]
    DESCRIPTION: str = PYPROJECT_CONTENT["description"]
    LIMITED_RATE: tuple[int, int] = (20, 10)

    WEB_SENTRY_DSN: str | None = None
    CELERY_SENTRY_DSN: str | None = None
    SENTRY_SAMPLE_RATE: float | None = 1.0
    SENTRY_TRACES_SAMPLE_RATE: float | None = 1.0

    SQLALCHEMY_DATABASE_URI: str
    DATABASE_POOL_SIZE: int | None = 50
    DATABASE_POOL_MAX_OVERFLOW: int | None = 10
    REDIS_DSN: str

    ENV: str = Env.DEV.name

    model_config = SettingsConfigDict(env_file=f"{PROJECT_DIR}/.env", case_sensitive=True, extra="allow")


settings = Settings()
