from pydantic import BaseModel


class GetUserQuery(BaseModel):
    user_id: int


class GetPlanQuery(BaseModel):
    plan_id: int


class GetSubscriptionQuery(BaseModel):
    subscription_id: int


class ListSubscriptionsQuery(BaseModel):
    user_id: int | None = None


class ListTrafficUsagesQuery(BaseModel):
    subscription_id: int
