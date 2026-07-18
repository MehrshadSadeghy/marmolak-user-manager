from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vpn_core.common.db.sqlalchemy_base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    telegram_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    chat_id: Mapped[str] = mapped_column(String(64), index=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    blocked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    blocked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocked_by_admin_telegram_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_collaborator: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    subscription_token: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    subscriptions: Mapped[list["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
    )
    collaborator_discount_rules: Mapped[list["CollaboratorDiscountRule"]] = relationship(
        "CollaboratorDiscountRule",
        back_populates="user",
        cascade="all, delete-orphan",
    )
