from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from vpn_core.common.db.sqlalchemy_base import Base
from vpn_core.server_management_domain.domain.server import ServerStatus


class ServerORM(Base):
    __tablename__ = "servers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(128), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)

    cpu_cores: Mapped[int] = mapped_column(Integer, nullable=False)
    ram_mb: Mapped[int] = mapped_column(Integer, nullable=False)
    disk_gb: Mapped[int] = mapped_column(Integer, nullable=False)

    host: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    ssh_port: Mapped[int] = mapped_column(Integer, default=22, nullable=False)
    api_port: Mapped[int] = mapped_column(Integer, nullable=False)

    max_users: Mapped[int] = mapped_column(Integer, default=100)
    current_users: Mapped[int] = mapped_column(Integer, default=0)
    max_bandwidth_mbps: Mapped[int] = mapped_column(Integer, nullable=False)

    cpu_usage: Mapped[float] = mapped_column(Float, default=0.0)
    ram_usage: Mapped[float] = mapped_column(Float, default=0.0)
    disk_usage: Mapped[float] = mapped_column(Float, default=0.0)
    network_in: Mapped[int] = mapped_column(Integer, default=0)
    network_out: Mapped[int] = mapped_column(Integer, default=0)

    xray_inbound_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)

    openvpn_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    node_api_secret: Mapped[str | None] = mapped_column(String(256), nullable=True)
    vpn_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    vpn_port: Mapped[int] = mapped_column(Integer, default=1433, nullable=False)
    vpn_proto: Mapped[str] = mapped_column(String(16), default="udp", nullable=False)

    status: Mapped[ServerStatus] = mapped_column(
        Enum(ServerStatus, name="server_status"),
        default=ServerStatus.offline,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    last_health_check_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
