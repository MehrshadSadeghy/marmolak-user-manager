from pydantic import BaseModel, Field

import yaml
from pathlib import Path
from pydantic_settings import SettingsConfigDict

class APIConfig(BaseModel):
    debug: bool
    host: str
    port: int
    title: str
    version: str

class DatabaseConfig(BaseModel):
    host: str
    port: int
    database: str
    username: str
    pg_password: str

class AIModelConfig(BaseModel):
    model: str = Field(alias="name")
    temperature: float | None
    timeout: int | None
    max_tokens: int | None
    model_provider: str | None
    streaming: bool | None

class Config(BaseModel):
    model_config = SettingsConfigDict(
        env_prefix="RAYA_TRADE_APP_",
    )


    api: APIConfig
    postgres: DatabaseConfig
    ai: AIModelConfig = Field(alias="ai_model_config")


    @classmethod
    def from_yaml(cls, environment: str):
        path = Path(__file__).parent.parent.parent / "config" / f"{environment}.yaml"
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        return cls(**data)
