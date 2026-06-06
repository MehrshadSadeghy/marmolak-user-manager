from pydantic import BaseModel

from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus


class CreateSubscriptionCommand(BaseModel):
    user_id: int
    plan_id: int
    service_type: str
    uuid: str | None = None


class RenewSubscriptionCommand(BaseModel):
    subscription_id: int
    plan_id: int


class UpdateSubscriptionStatusCommand(BaseModel):
    subscription_id: int
    status: SubscriptionStatus
