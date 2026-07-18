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
                    "subscription_token": "VARCHAR(64)",
                }
                for column_name, column_type in user_patches.items():
                    if column_name not in user_columns:
                        conn.execute(
                            text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
                        )
                conn.execute(
                    text(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_subscription_token "
                        "ON users (subscription_token) "
                        "WHERE subscription_token IS NOT NULL"
                    )
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
                credential_patches = {
                    "auth_mode": "VARCHAR(32) NOT NULL DEFAULT 'certificate'",
                    "vpn_username": "VARCHAR(32)",
                    "password_hash": "VARCHAR(255)",
                    "password_rotated_at": "TIMESTAMP WITH TIME ZONE",
                    "auth_synced_at": "TIMESTAMP WITH TIME ZONE",
                }
                for column_name, column_type in credential_patches.items():
                    if column_name not in credential_columns:
                        conn.execute(
                            text(
                                f"ALTER TABLE openvpn_client_credentials "
                                f"ADD COLUMN {column_name} {column_type}"
                            )
                        )

            if "servers" in table_names:
                server_columns = {
                    column["name"] for column in inspector.get_columns("servers")
                }
                server_patches = {
                    "v2ray_enabled": "BOOLEAN NOT NULL DEFAULT FALSE",
                    "v2ray_node_api_secret": "VARCHAR(256)",
                    "v2ray_node_api_port": "INTEGER NOT NULL DEFAULT 8092",
                    "v2ray_vpn_host": "VARCHAR(255)",
                    "v2ray_vpn_port": "INTEGER NOT NULL DEFAULT 443",
                    "v2ray_ws_path": "VARCHAR(255) NOT NULL DEFAULT '/v2ray'",
                    "v2ray_network": "VARCHAR(16) NOT NULL DEFAULT 'ws'",
                    "v2ray_security": "VARCHAR(16) NOT NULL DEFAULT 'tls'",
                    "v2ray_sni": "VARCHAR(255)",
                    "v2ray_fingerprint": "VARCHAR(32)",
                }
                for column_name, column_type in server_patches.items():
                    if column_name not in server_columns:
                        conn.execute(
                            text(f"ALTER TABLE servers ADD COLUMN {column_name} {column_type}")
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
