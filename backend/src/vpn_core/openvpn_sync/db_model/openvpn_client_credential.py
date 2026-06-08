from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from vpn_core.common.db.sqlalchemy_base import Base


class OpenVpnClientCredentialORM(Base):
    __tablename__ = "openvpn_client_credentials"
    __table_args__ = (
        UniqueConstraint("server_id", "common_name", name="uq_openvpn_server_common_name"),
        UniqueConstraint("user_id", "server_id", "slot_index", name="uq_openvpn_user_server_slot"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    server_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    telegram_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    common_name: Mapped[str] = mapped_column(String(255), nullable=False)
    slot_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ovpn_content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    last_status_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
