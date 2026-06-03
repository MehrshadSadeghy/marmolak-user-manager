from typing import Callable

from sqlalchemy import Engine, func
from sqlalchemy.orm import Session, DeclarativeBase

from vpn_core.config import DatabaseConfig
from vpn_core.core.db.base import BaseDatabase
from vpn_core.core.manager.base import Manager


class PostgresManager(Manager):
    def __init__(
        self,
        provider: BaseDatabase,
        base: type[DeclarativeBase],
        session_factory: Callable,
    ):
        self._provider = provider
        self._engine = None
        self._session = session_factory
        self._base = base

    async def setup(self) -> None:
        url = self._provider.create_url()
        self._engine = self._provider.create_engine(url)

        self._base.metadata.create_all(bind=self._engine)
        self._session = self._provider.setup_session(self._engine)

    async def run(self) -> None:
        pass

    async def teardown(self) -> None:
        pass

    def get_session(self, ):
        db = self._session()
        try:
            yield db
        finally:
            db.close()
