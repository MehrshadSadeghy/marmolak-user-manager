from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from vpn_core.common.db.sqlalchemy_base import Base
from vpn_core.traffic_monitoring_domain.domain.connection_log import ConnectionEvent
from vpn_core.traffic_monitoring_domain.domain.quota_signal import QuotaSignalType
from vpn_core.traffic_monitoring_domain.domain.traffic_sample import ConnectionType


class TrafficSampleORM(Base):
    __tablename__ = "tm_traffic_samples"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    uuid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id"),
        nullable=False,
        index=True,
    )

    upload_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    download_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    connection_type: Mapped[ConnectionType] = mapped_column(
        Enum(ConnectionType, name="tm_connection_type"),
        default=ConnectionType.unknown,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class TrafficAggregationORM(Base):
    __tablename__ = "tm_traffic_aggregations"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    uuid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=True,
        index=True,
    )
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id"),
        nullable=True,
        index=True,
    )

    upload_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    download_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class UsageHistoryORM(Base):
    __tablename__ = "tm_usage_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=False,
        index=True,
    )
    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id"),
        nullable=True,
        index=True,
    )

    used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class RealtimeSnapshotORM(Base):
    __tablename__ = "tm_realtime_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id"),
        nullable=False,
        index=True,
    )

    active_users: Mapped[int] = mapped_column(Integer, default=0)
    bandwidth_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    upload_bps: Mapped[int] = mapped_column(BigInteger, default=0)
    download_bps: Mapped[int] = mapped_column(BigInteger, default=0)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ConnectionLogORM(Base):
    __tablename__ = "tm_connection_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    uuid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    subscription_id: Mapped[int | None] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=True,
        index=True,
    )
    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id"),
        nullable=False,
        index=True,
    )

    event: Mapped[ConnectionEvent] = mapped_column(
        Enum(ConnectionEvent, name="tm_connection_event"),
        nullable=False,
        index=True,
    )
    connection_type: Mapped[ConnectionType] = mapped_column(
        Enum(ConnectionType, name="tm_connection_type", create_type=False),
        default=ConnectionType.unknown,
    )

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class HealthMetricORM(Base):
    __tablename__ = "tm_health_metrics"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    server_id: Mapped[int] = mapped_column(
        ForeignKey("servers.id"),
        nullable=False,
        index=True,
    )

    cpu_usage: Mapped[float] = mapped_column(Float, default=0.0)
    ram_usage: Mapped[float] = mapped_column(Float, default=0.0)
    disk_usage: Mapped[float] = mapped_column(Float, default=0.0)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class QuotaSignalORM(Base):
    __tablename__ = "tm_quota_signals"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"),
        nullable=False,
        index=True,
    )
    uuid: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    signal_type: Mapped[QuotaSignalType] = mapped_column(
        Enum(QuotaSignalType, name="tm_quota_signal_type"),
        nullable=False,
        index=True,
    )
    used_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    limit_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
