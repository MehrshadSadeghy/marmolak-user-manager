from abc import ABC, abstractmethod

from vpn_core.subscription_domain.domain.plan import Plan
from vpn_core.subscription_domain.domain.queries import (
    GetPlanQuery,
    GetSubscriptionQuery,
    GetUserQuery,
    ListPlansQuery,
    ListSubscriptionsQuery,
    ListTrafficUsagesQuery,
)
from vpn_core.subscription_domain.domain.subscription import Subscription
from vpn_core.subscription_domain.domain.traffic import TrafficUsage
from vpn_core.subscription_domain.domain.user import User


class SubscriptionRepository(ABC):
    @abstractmethod
    async def create_user(self, user: User) -> User:
        pass

    @abstractmethod
    async def get_user(self, query: GetUserQuery) -> User | None:
        pass

    @abstractmethod
    async def update_user(self, user: User) -> User | None:
        pass

    @abstractmethod
    async def list_users(self) -> list[User]:
        pass

    @abstractmethod
    async def create_plan(self, plan: Plan) -> Plan:
        pass

    @abstractmethod
    async def get_plan(self, query: GetPlanQuery) -> Plan | None:
        pass

    @abstractmethod
    async def list_plans(self, query: ListPlansQuery | None = None) -> list[Plan]:
        pass

    @abstractmethod
    async def update_plan(self, plan: Plan) -> Plan | None:
        pass

    @abstractmethod
    async def delete_plan(self, plan_id: int) -> bool:
        pass

    @abstractmethod
    async def create_subscription(self, subscription: Subscription) -> Subscription:
        pass

    @abstractmethod
    async def get_subscription(self, query: GetSubscriptionQuery) -> Subscription | None:
        pass

    @abstractmethod
    async def list_subscriptions(self, query: ListSubscriptionsQuery) -> list[Subscription]:
        pass

    @abstractmethod
    async def update_subscription(self, subscription: Subscription) -> Subscription | None:
        pass

    @abstractmethod
    async def create_traffic_usage(self, traffic: TrafficUsage) -> TrafficUsage:
        pass

    @abstractmethod
    async def list_traffic_usages(self, query: ListTrafficUsagesQuery) -> list[TrafficUsage]:
        pass
