from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vpn_core.common.db.sqlalchemy_base import Base


class CollaboratorDiscountRule(Base):
    __tablename__ = "collaborator_discount_rules"
    __table_args__ = (
        UniqueConstraint("user_id", "service_type", name="uq_collaborator_discount_user_service"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    service_type: Mapped[str] = mapped_column(String(32), index=True)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship("User", back_populates="collaborator_discount_rules")
