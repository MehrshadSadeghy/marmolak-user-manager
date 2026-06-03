from vpn_core.config import DatabaseConfig
from vpn_core.core.db.base import BaseDatabase
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session

class Postgres(BaseDatabase):
    def __init__(self, config:DatabaseConfig) -> None:
        self._config = config
        self._session_local = None
        self._url = None

    def create_url(self) -> str:
        return f"postgresql://{self._config.username}:{self._config.pg_password}@{self._config.host}:{self._config.port}/{self._config.database}"

    def create_engine(self, url: str) -> Engine:

        self._url = url
        return create_engine(url=url)

    def setup_session(self, engine: Engine):
        self._session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )
        return self._session_local

    def get_session(self, engine: Engine) -> Session:
        if not self._session_local:
            self.setup_session(engine)

        return self._session_local()

    def close_session(self):
        if self._engine:
            self._engine.dispose()
