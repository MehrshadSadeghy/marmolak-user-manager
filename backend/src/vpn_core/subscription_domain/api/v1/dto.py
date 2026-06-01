from pydantic import BaseModel

from vpn_core.subscription_domain.domain.commands import (
    CreateSubscriptionCommand,
    UpdateSubscriptionStatusCommand,
)
from vpn_core.subscription_domain.domain.plan import Plan
from vpn_core.subscription_domain.domain.queries import (
    GetPlanQuery,
    GetSubscriptionQuery,
    GetUserQuery,
    ListSubscriptionsQuery,
    ListTrafficUsagesQuery,
)
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus
from vpn_core.subscription_domain.domain.traffic import TrafficUsage
from vpn_core.subscription_domain.domain.user import User


class CreateUserDTO(BaseModel):
    telegram_id: str
    chat_id: str
    is_active: bool = True

    def to_domain(self) -> User:
        return User(
            telegram_id=self.telegram_id,
            chat_id=self.chat_id,
            is_active=self.is_active,
        )


class UserResponseDTO(BaseModel):
    user: User


class UserListResponseDTO(BaseModel):
    users: list[User]


class CreatePlanDTO(BaseModel):
    name: str
    description: str = ""
    duration_days: int
    traffic_limit_bytes: int
    is_active: bool = True

    def to_domain(self) -> Plan:
        return Plan(
            name=self.name,
            description=self.description,
            duration_days=self.duration_days,
            traffic_limit_bytes=self.traffic_limit_bytes,
            is_active=self.is_active,
        )


class PlanResponseDTO(BaseModel):
    plan: Plan


class PlanListResponseDTO(BaseModel):
    plans: list[Plan]


class CreateSubscriptionDTO(BaseModel):
    user_id: int
    plan_id: int
    uuid: str | None = None

    def to_domain(self) -> CreateSubscriptionCommand:
        return CreateSubscriptionCommand(
            user_id=self.user_id,
            plan_id=self.plan_id,
            uuid=self.uuid,
        )


class SubscriptionResponseDTO(BaseModel):
    subscription: Subscription


class SubscriptionListResponseDTO(BaseModel):
    subscriptions: list[Subscription]


class UpdateSubscriptionStatusDTO(BaseModel):
    status: SubscriptionStatus

    def to_domain(self, subscription_id: int) -> UpdateSubscriptionStatusCommand:
        return UpdateSubscriptionStatusCommand(
            subscription_id=subscription_id,
            status=self.status,
        )


class CreateTrafficUsageDTO(BaseModel):
    subscription_id: int
    uuid: str
    server_id: int | None = None
    upload_bytes: int = 0
    download_bytes: int = 0
    total_bytes: int = 0
    interval_seconds: int = 60

    def to_domain(self) -> TrafficUsage:
        return TrafficUsage(
            subscription_id=self.subscription_id,
            server_id=self.server_id,
            uuid=self.uuid,
            upload_bytes=self.upload_bytes,
            download_bytes=self.download_bytes,
            total_bytes=self.total_bytes,
            interval_seconds=self.interval_seconds,
        )


class TrafficUsageResponseDTO(BaseModel):
    traffic_usage: TrafficUsage


class TrafficUsageListResponseDTO(BaseModel):
    traffic_usages: list[TrafficUsage]


class GetUserQueryDTO(BaseModel):
    user_id: int

    def to_domain(self) -> GetUserQuery:
        return GetUserQuery(user_id=self.user_id)


class GetPlanQueryDTO(BaseModel):
    plan_id: int

    def to_domain(self) -> GetPlanQuery:
        return GetPlanQuery(plan_id=self.plan_id)


class GetSubscriptionQueryDTO(BaseModel):
    subscription_id: int

    def to_domain(self) -> GetSubscriptionQuery:
        return GetSubscriptionQuery(subscription_id=self.subscription_id)


class ListSubscriptionsQueryDTO(BaseModel):
    user_id: int | None = None

    def to_domain(self) -> ListSubscriptionsQuery:
        return ListSubscriptionsQuery(user_id=self.user_id)


class ListTrafficUsagesQueryDTO(BaseModel):
    subscription_id: int

    def to_domain(self) -> ListTrafficUsagesQuery:
        return ListTrafficUsagesQuery(subscription_id=self.subscription_id)
