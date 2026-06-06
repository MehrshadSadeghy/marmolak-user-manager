from sqlalchemy.orm import DeclarativeBase, sessionmaker

from vpn_core.core.db.base import BaseDatabase
from vpn_core.core.manager.base import Manager


class PostgresManager(Manager):
    def __init__(
        self,
        provider: BaseDatabase,
        base: type[DeclarativeBase],
    ):
        self._provider = provider
        self._base = base
        self._engine = None
        self._sessionmaker: sessionmaker | None = None

    async def setup(self) -> None:
        url = self._provider.create_url()
        self._engine = self._provider.create_engine(url)
        self._base.metadata.create_all(bind=self._engine)
        self._sessionmaker = self._provider.setup_session(self._engine)

    async def run(self) -> None:
        pass

    async def teardown(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    def create_session(self):
        if self._sessionmaker is None:
            raise RuntimeError("PostgresManager is not setup")
        return self._sessionmaker()
