from pydantic import BaseModel

from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus


class CreateSubscriptionCommand(BaseModel):
    user_id: int
    plan_id: int
    uuid: str | None = None


class UpdateSubscriptionStatusCommand(BaseModel):
    subscription_id: int
    status: SubscriptionStatus
