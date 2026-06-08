from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CollaboratorDiscountRule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    service_type: str
    discount_percent: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminAuditLogEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    admin_telegram_id: str
    action: str
    target_user_id: int | None = None
    target_config_id: str | None = None
    details: dict | None = None
    created_at: datetime | None = None


class AdminUserListItem(BaseModel):
    id: int
    telegram_id: str
    username: str | None = None
    created_at: datetime | None = None
    active_configs_count: int = 0
    is_blocked: bool = False
    is_collaborator: bool = False


class PaginatedUsers(BaseModel):
    items: list[AdminUserListItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class AdminUserDetail(BaseModel):
    id: int
    telegram_id: str
    username: str | None = None
    created_at: datetime | None = None
    total_purchased_plans: int = 0
    total_active_configs: int = 0
    total_traffic_used_bytes: int = 0
    is_blocked: bool = False
    is_collaborator: bool = False
    discount_rules: list[CollaboratorDiscountRule] = Field(default_factory=list)


class AdminUserConfigItem(BaseModel):
    id: int
    config_id: str
    created_at: datetime | None = None
    expire_at: datetime | None = None
    traffic_limit_bytes: int = 0
    traffic_used_bytes: int = 0
    remaining_traffic_bytes: int = 0
    status: str
    subscription_id: int | None = None
    service_type: str | None = None


class AdminUserConfigDetail(AdminUserConfigItem):
    ovpn_content: str | None = None
