from datetime import datetime

from sqlalchemy import DateTime, Integer, func
from sqlalchemy.orm import Mapped, mapped_column

from vpn_core.common.db.sqlalchemy_base import Base


class OpenVpnTrafficUsageORM(Base):
    __tablename__ = "openvpn_traffic_usage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    subscription_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    bytes_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
