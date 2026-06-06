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
        self._apply_schema_patches()
        self._sessionmaker = self._provider.setup_session(self._engine)

    def _apply_schema_patches(self) -> None:
        from sqlalchemy import inspect, text

        if self._engine is None:
            return
        with self._engine.begin() as conn:
            inspector = inspect(conn)
            if "payment_methods" not in inspector.get_table_names():
                return
            columns = {column["name"] for column in inspector.get_columns("payment_methods")}
            if "card_numbers" not in columns:
                conn.execute(
                    text(
                        "ALTER TABLE payment_methods "
                        "ADD COLUMN card_numbers JSONB NOT NULL DEFAULT '[]'::jsonb"
                    )
                )

    async def run(self) -> None:
        pass

    async def teardown(self) -> None:
        if self._engine is not None:
            self._engine.dispose()

    def create_session(self):
        if self._sessionmaker is None:
            raise RuntimeError("PostgresManager is not setup")
        return self._sessionmaker()
