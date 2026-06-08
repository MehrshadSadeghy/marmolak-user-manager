from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AdminUserListItemDTO(BaseModel):
    id: int
    telegram_id: str
    username: str | None = None
    created_at: datetime | None = None
    active_configs_count: int = 0
    is_blocked: bool = False
    is_collaborator: bool = False


class PaginatedUsersResponseDTO(BaseModel):
    users: list[AdminUserListItemDTO]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class CollaboratorDiscountRuleDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    user_id: int
    service_type: str
    discount_percent: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AdminUserDetailDTO(BaseModel):
    id: int
    telegram_id: str
    username: str | None = None
    created_at: datetime | None = None
    total_purchased_plans: int = 0
    total_active_configs: int = 0
    total_traffic_used_bytes: int = 0
    is_blocked: bool = False
    is_collaborator: bool = False
    discount_rules: list[CollaboratorDiscountRuleDTO] = Field(default_factory=list)


class AdminUserConfigItemDTO(BaseModel):
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


class AdminUserConfigDetailDTO(AdminUserConfigItemDTO):
    ovpn_content: str | None = None


class AdminUserConfigListResponseDTO(BaseModel):
    configs: list[AdminUserConfigItemDTO]


class BlockUserDTO(BaseModel):
    reason: str | None = None


class AddCollaboratorDiscountDTO(BaseModel):
    discount_percent: int
    service_type: str


class UserAccessStatusDTO(BaseModel):
    user_id: int
    is_blocked: bool
