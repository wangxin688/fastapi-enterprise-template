import tomllib
from enum import StrEnum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_DIR = Path(__file__).parent.parent.parent
with Path.open(Path(f"{PROJECT_DIR}/pyproject.toml"), "rb") as f:
    PYPROJECT_CONTENT = tomllib.load(f)["project"]


class _Env(StrEnum):
    DEV = "dev"
    PROD = "prod"
    STAGE = "stage"


class Settings(BaseSettings):
    SECRET_KEY: str = Field(default="ea90084454f1f94244f779d605286ae482ffb1f33570dcd1f6a683e5c002b492")
    SECURITY_BCRYPT_ROUNDS: int = Field(default=4)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=120)
    REFRESH_TOKEN_EXPIRE_MINUTES: int = Field(default=11520)
    BACKEND_CORS: list[str] = Field(default=["*"])
    ALLOWED_HOST: list[str] = Field(default=["*"])
    BASE_URL: str = Field(default="http://localhost:8000")

    PROJECT_NAME: str = Field(default=PYPROJECT_CONTENT["name"])
    VERSION: str = Field(default=PYPROJECT_CONTENT["version"])
    DESCRIPTION: str = Field(default=PYPROJECT_CONTENT["description"])
    ENABLE_LIMIT: bool = Field(default=False)
    LIMITED_RATE: tuple[int, int] = Field(default=(20, 10))

    WEB_SENTRY_DSN: str | None = Field(default=None)
    CELERY_SENTRY_DSN: str | None = Field(default=None)
    SENTRY_SAMPLE_RATE: float = Field(default=1.0, gt=0.0, le=1.0)
    SENTRY_TRACES_SAMPLE_RATE: float | None = Field(default=None, gt=0.0, le=1.0)

    SQLALCHEMY_DATABASE_URI: str = Field(
        default="postgresql+asyncpg://demo:91fb8e9e009f5b9ce1854d947e6fe4a3@localhost:5432/demo"
    )
    DATABASE_POOL_SIZE: int | None = Field(default=50)
    DATABASE_POOL_MAX_OVERFLOW: int | None = Field(default=10)
    REDIS_DSN: str = Field(default="redis://:cfe1c2c4703abb205d71abdc07cc3f3d@localhost:6379")

    ENV: str = _Env.DEV.name

    model_config = SettingsConfigDict(env_file=f"{PROJECT_DIR}/.env", case_sensitive=True, extra="allow")


settings = Settings()
