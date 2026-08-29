"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Database
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost/poker_trainer",
        alias="DATABASE_URL",
    )

    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # JWT
    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=1, alias="API_WORKERS")

    # Solver
    solver_default_iterations: int = Field(default=25000, alias="SOLVER_DEFAULT_ITERATIONS")
    solver_save_every: int = Field(default=10000, alias="SOLVER_SAVE_EVERY")
    solver_report_every: int = Field(default=5000, alias="SOLVER_REPORT_EVERY")

    # Paths
    solutions_dir: Path = Field(default=Path("/home/tuanlinh/poker/solutions"), alias="SOLUTIONS_DIR")
    model_cache_dir: Path = Field(default=Path("/home/tuanlinh/poker/.model_cache"), alias="MODEL_CACHE_DIR")

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()