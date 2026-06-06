from pydantic import BaseModel


class GetUserQuery(BaseModel):
    user_id: int | None = None
    telegram_id: str | None = None


class GetPlanQuery(BaseModel):
    plan_id: int


class ListPlansQuery(BaseModel):
    service_type: str | None = None
    active_only: bool = False


class GetSubscriptionQuery(BaseModel):
    subscription_id: int


class ListSubscriptionsQuery(BaseModel):
    user_id: int | None = None


class ListTrafficUsagesQuery(BaseModel):
    subscription_id: int
