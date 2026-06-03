import uuid
from uuid import UUID

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from vpn_core.common.db.sqlalchemy_base import Base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID



class StrategyORM(Base):
    __tablename__ = "strategies"

    id = Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        index=True,
        default=uuid.uuid4
    )

    name = Column(String, nullable=False)

    data = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
