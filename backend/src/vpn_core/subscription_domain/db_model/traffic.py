from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vpn_core.common.db.sqlalchemy_base import Base


class TrafficUsage(Base):
    __tablename__ = "traffic_usages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    subscription_id: Mapped[int] = mapped_column(
        ForeignKey("subscriptions.id"),
        index=True,
    )

    server_id: Mapped[int | None] = mapped_column(
        ForeignKey("servers.id"),
        nullable=True,
        index=True,
    )

    uuid: Mapped[str] = mapped_column(String(64), index=True)

    upload_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    download_bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    total_bytes: Mapped[int] = mapped_column(BigInteger, default=0)

    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        index=True,
    )

    interval_seconds: Mapped[int] = mapped_column(Integer, default=60)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    subscription: Mapped["Subscription"] = relationship(
        "Subscription",
        back_populates="traffic_usages",
    )
