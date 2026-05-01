from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "BenchmarkDashboard API"
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/benchmark_dashboard"
    data_dir: Path = Path("../data")
    auto_ingest_data: bool = True
    data_refresh_interval_seconds: float = 2.0
    cors_origins: list[str] = ["http://localhost:5173"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: Any) -> list[str] | Any:
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value.startswith("["):
                try:
                    parsed_value = json.loads(stripped_value)
                except json.JSONDecodeError:
                    parsed_value = None
                if isinstance(parsed_value, list):
                    return [str(origin).strip() for origin in parsed_value if str(origin).strip()]
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
