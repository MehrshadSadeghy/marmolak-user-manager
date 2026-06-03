import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict

DEFAULT_POSTGRES_DB = "user_manager_db"
DEFAULT_POSTGRES_USER = "user_manager_user"
DEFAULT_POSTGRES_PASSWORD = "changeme_postgres"


class APIConfig(BaseModel):
    debug: bool
    host: str
    port: int
    title: str
    version: str


class DatabaseConfig(BaseModel):
    host: str
    port: int
    database: str = DEFAULT_POSTGRES_DB
    username: str = DEFAULT_POSTGRES_USER
    pg_password: str = DEFAULT_POSTGRES_PASSWORD


def backend_root_directory() -> Path:
    return Path(__file__).resolve().parents[2]


def _apply_env_overrides(data: dict) -> None:
    postgres = data.setdefault("postgres", {})
    if host := os.getenv("POSTGRES_HOST"):
        postgres["host"] = host
    postgres["database"] = os.getenv("POSTGRES_DB", DEFAULT_POSTGRES_DB)
    postgres["username"] = os.getenv("POSTGRES_USER", DEFAULT_POSTGRES_USER)
    postgres["pg_password"] = os.getenv("POSTGRES_PASSWORD", DEFAULT_POSTGRES_PASSWORD)


class Config(BaseModel):
    model_config = SettingsConfigDict(
        env_prefix="RAYA_TRADE_APP_",
    )

    api: APIConfig
    postgres: DatabaseConfig

    @classmethod
    def from_yaml(cls, environment: str):
        backend = backend_root_directory()
        load_dotenv(backend / ".env")
        load_dotenv(backend.parent / ".env")

        path = backend / "config" / f"{environment}.yaml"
        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        _apply_env_overrides(data)
        return cls(**data)
