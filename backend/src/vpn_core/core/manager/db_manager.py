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
            table_names = set(inspector.get_table_names())

            if "payment_methods" in table_names:
                columns = {column["name"] for column in inspector.get_columns("payment_methods")}
                if "card_numbers" not in columns:
                    conn.execute(
                        text(
                            "ALTER TABLE payment_methods "
                            "ADD COLUMN card_numbers JSONB NOT NULL DEFAULT '[]'::jsonb"
                        )
                    )

            if "users" in table_names:
                user_columns = {column["name"] for column in inspector.get_columns("users")}
                user_patches = {
                    "is_blocked": "BOOLEAN NOT NULL DEFAULT FALSE",
                    "blocked_at": "TIMESTAMP WITH TIME ZONE",
                    "blocked_reason": "TEXT",
                    "blocked_by_admin_telegram_id": "VARCHAR(64)",
                    "is_collaborator": "BOOLEAN NOT NULL DEFAULT FALSE",
                }
                for column_name, column_type in user_patches.items():
                    if column_name not in user_columns:
                        conn.execute(
                            text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                        )

            if "openvpn_client_credentials" in table_names:
                credential_columns = {
                    column["name"]
                    for column in inspector.get_columns("openvpn_client_credentials")
                }
                if "last_status_bytes" not in credential_columns:
                    conn.execute(
                        text(
                            "ALTER TABLE openvpn_client_credentials "
                            "ADD COLUMN last_status_bytes BIGINT NOT NULL DEFAULT 0"
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
