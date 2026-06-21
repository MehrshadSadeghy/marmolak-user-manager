from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from vpn_core.common.db.sqlalchemy_base import Base


class PasarguardPanelLinkORM(Base):
    __tablename__ = "pasarguard_panel_links"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, index=True)
    subscription_token: Mapped[str] = mapped_column(String(256), nullable=False)
    panel_username: Mapped[str] = mapped_column(String(128), nullable=False)
    subscription_url: Mapped[str] = mapped_column(Text, nullable=False)

    linked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
