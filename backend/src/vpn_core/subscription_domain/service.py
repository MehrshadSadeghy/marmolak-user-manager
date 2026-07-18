import secrets
from datetime import UTC, datetime, timedelta

from vpn_core.subscription_domain.domain.commands import (
    CreateSubscriptionCommand,
    RenewSubscriptionCommand,
    UpdateSubscriptionStatusCommand,
)
from vpn_core.subscription_domain.domain.plan import Plan
from vpn_core.subscription_domain.domain.queries import (
    GetPlanQuery,
    GetSubscriptionQuery,
    GetUserQuery,
    ListPlansQuery,
    ListSubscriptionsQuery,
    ListTrafficUsagesQuery,
)
from vpn_core.subscription_domain.domain.subscription import Subscription, SubscriptionStatus
from vpn_core.subscription_domain.domain.traffic import TrafficUsage
from vpn_core.subscription_domain.domain.user import User
from vpn_core.subscription_domain.repository.base import SubscriptionRepository


class SubscriptionService:
    def __init__(self, repository: SubscriptionRepository):
        self._repository = repository

    async def create_user(self, user: User) -> User:
        return await self._repository.create_user(user)

    async def get_or_create_user(self, user: User) -> User:
        existing = await self._repository.get_user(
            GetUserQuery(telegram_id=user.telegram_id)
        )
        if existing:
            existing.chat_id = user.chat_id
            existing.username = user.username
            updated = await self._repository.update_user(existing)
            return await self.ensure_subscription_token(updated or existing)
        created = await self._repository.create_user(
            user.model_copy(update={"subscription_token": self._generate_subscription_token()})
        )
        return created

    async def ensure_subscription_token(self, user: User) -> User:
        if user.subscription_token or user.id is None:
            return user
        user.subscription_token = self._generate_subscription_token()
        updated = await self._repository.update_user(user)
        return updated or user

    @staticmethod
    def _generate_subscription_token() -> str:
        return secrets.token_urlsafe(24)

    async def get_user(self, query: GetUserQuery) -> User | None:
        return await self._repository.get_user(query)

    async def list_users(self) -> list[User]:
        return await self._repository.list_users()

    async def create_plan(self, plan: Plan) -> Plan:
        return await self._repository.create_plan(plan)

    async def update_plan(self, plan: Plan) -> Plan | None:
        return await self._repository.update_plan(plan)

    async def delete_plan(self, plan_id: int) -> bool:
        return await self._repository.delete_plan(plan_id)

    async def get_plan(self, query: GetPlanQuery) -> Plan | None:
        return await self._repository.get_plan(query)

    async def list_plans(self, query: ListPlansQuery | None = None) -> list[Plan]:
        return await self._repository.list_plans(query)

    async def create_subscription(self, command: CreateSubscriptionCommand) -> Subscription | None:
        user = await self._repository.get_user(GetUserQuery(user_id=command.user_id))
        if not user:
            return None

        plan = await self._repository.get_plan(GetPlanQuery(plan_id=command.plan_id))
        if not plan:
            return None

        subscription = Subscription(
            user_id=command.user_id,
            plan_id=command.plan_id,
            service_type=command.service_type or plan.service_type,
            uuid=command.uuid or str(uuid.uuid4()),
            traffic_limit_bytes=plan.traffic_limit_bytes,
            expire_at=datetime.now(UTC) + timedelta(days=plan.duration_days),
        )
        return await self._repository.create_subscription(subscription)

    async def renew_subscription(self, command: RenewSubscriptionCommand) -> Subscription | None:
        subscription = await self._repository.get_subscription(
            GetSubscriptionQuery(subscription_id=command.subscription_id)
        )
        if not subscription:
            return None

        plan = await self._repository.get_plan(GetPlanQuery(plan_id=command.plan_id))
        if not plan:
            return None

        now = datetime.now(UTC)
        base = subscription.expire_at if subscription.expire_at > now else now
        subscription.plan_id = plan.id
        subscription.service_type = plan.service_type
        subscription.traffic_limit_bytes = plan.traffic_limit_bytes
        subscription.traffic_used_bytes = 0
        subscription.expire_at = base + timedelta(days=plan.duration_days)
        subscription.status = SubscriptionStatus.active
        return await self._repository.update_subscription(subscription)

    async def get_subscription(self, query: GetSubscriptionQuery) -> Subscription | None:
        return await self._repository.get_subscription(query)

    async def list_subscriptions(self, query: ListSubscriptionsQuery) -> list[Subscription]:
        return await self._repository.list_subscriptions(query)

    async def update_subscription_status(
        self,
        command: UpdateSubscriptionStatusCommand,
    ) -> Subscription | None:
        subscription = await self._repository.get_subscription(
            GetSubscriptionQuery(subscription_id=command.subscription_id)
        )
        if not subscription:
            return None

        subscription.status = command.status
        return await self._repository.update_subscription(subscription)

    async def record_traffic_usage(self, traffic: TrafficUsage) -> TrafficUsage | None:
        subscription = await self._repository.get_subscription(
            GetSubscriptionQuery(subscription_id=traffic.subscription_id)
        )
        if not subscription:
            return None

        if traffic.total_bytes == 0:
            traffic.total_bytes = traffic.upload_bytes + traffic.download_bytes

        created = await self._repository.create_traffic_usage(traffic)

        subscription.traffic_used_bytes += created.total_bytes
        if subscription.traffic_used_bytes >= subscription.traffic_limit_bytes > 0:
            subscription.status = SubscriptionStatus.traffic_exceeded

        await self._repository.update_subscription(subscription)
        return created

    async def list_traffic_usages(self, query: ListTrafficUsagesQuery) -> list[TrafficUsage]:
        return await self._repository.list_traffic_usages(query)
