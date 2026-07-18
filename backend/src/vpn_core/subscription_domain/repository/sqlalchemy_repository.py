from sqlalchemy.orm import Session

from vpn_core.subscription_domain.db_model.plan import Plan as PlanORM
from vpn_core.subscription_domain.db_model.subscription import Subscription as SubscriptionORM
from vpn_core.subscription_domain.db_model.traffic import TrafficUsage as TrafficUsageORM
from vpn_core.subscription_domain.db_model.user import User as UserORM
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
from vpn_core.subscription_domain.repository.base import SubscriptionRepository


class SubscriptionDBRepository(SubscriptionRepository):
    def __init__(self, session: Session):
        self._session = session

    async def create_user(self, user: User) -> User:
        obj = UserORM(
            telegram_id=user.telegram_id,
            chat_id=user.chat_id,
            username=user.username,
            is_active=user.is_active,
            subscription_token=user.subscription_token,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return User.model_validate(obj)

    async def get_user(self, query: GetUserQuery) -> User | None:
        if query.user_id is not None:
            obj = self._session.get(UserORM, query.user_id)
        elif query.telegram_id is not None:
            obj = (
                self._session.query(UserORM)
                .filter(UserORM.telegram_id == query.telegram_id)
                .one_or_none()
            )
        elif query.subscription_token is not None:
            obj = (
                self._session.query(UserORM)
                .filter(UserORM.subscription_token == query.subscription_token)
                .one_or_none()
            )
        else:
            return None
        if not obj:
            return None
        return User.model_validate(obj)

    async def update_user(self, user: User) -> User | None:
        obj = self._session.get(UserORM, user.id)
        if not obj:
            return None
        obj.chat_id = user.chat_id
        obj.username = user.username
        obj.is_active = user.is_active
        obj.is_blocked = user.is_blocked
        obj.blocked_at = user.blocked_at
        obj.blocked_reason = user.blocked_reason
        obj.blocked_by_admin_telegram_id = user.blocked_by_admin_telegram_id
        obj.is_collaborator = user.is_collaborator
        obj.subscription_token = user.subscription_token
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return User.model_validate(obj)

    async def list_users(self) -> list[User]:
        rows = self._session.query(UserORM).all()
        return [User.model_validate(row) for row in rows]

    async def create_plan(self, plan: Plan) -> Plan:
        obj = PlanORM(
            name=plan.name,
            description=plan.description,
            service_type=plan.service_type,
            duration_days=plan.duration_days,
            traffic_limit_bytes=plan.traffic_limit_bytes,
            price_toman=plan.price_toman,
            is_active=plan.is_active,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return Plan.model_validate(obj)

    async def get_plan(self, query: GetPlanQuery) -> Plan | None:
        obj = self._session.get(PlanORM, query.plan_id)
        if not obj:
            return None
        return Plan.model_validate(obj)

    async def list_plans(self, query: ListPlansQuery | None = None) -> list[Plan]:
        db_query = self._session.query(PlanORM)
        if query:
            if query.service_type is not None:
                db_query = db_query.filter(PlanORM.service_type == query.service_type)
            if query.active_only:
                db_query = db_query.filter(PlanORM.is_active.is_(True))
        rows = db_query.order_by(PlanORM.price_toman).all()
        return [Plan.model_validate(row) for row in rows]

    async def update_plan(self, plan: Plan) -> Plan | None:
        obj = self._session.get(PlanORM, plan.id)
        if not obj:
            return None
        obj.name = plan.name
        obj.description = plan.description
        obj.service_type = plan.service_type
        obj.duration_days = plan.duration_days
        obj.traffic_limit_bytes = plan.traffic_limit_bytes
        obj.price_toman = plan.price_toman
        obj.is_active = plan.is_active
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return Plan.model_validate(obj)

    async def delete_plan(self, plan_id: int) -> bool:
        obj = self._session.get(PlanORM, plan_id)
        if not obj:
            return False
        self._session.delete(obj)
        self._session.commit()
        return True

    async def create_subscription(self, subscription: Subscription) -> Subscription:
        obj = SubscriptionORM(
            user_id=subscription.user_id,
            plan_id=subscription.plan_id,
            service_type=subscription.service_type,
            uuid=subscription.uuid,
            status=subscription.status,
            traffic_limit_bytes=subscription.traffic_limit_bytes,
            traffic_used_bytes=subscription.traffic_used_bytes,
            expire_at=subscription.expire_at,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return Subscription.model_validate(obj)

    async def get_subscription(self, query: GetSubscriptionQuery) -> Subscription | None:
        obj = self._session.get(SubscriptionORM, query.subscription_id)
        if not obj:
            return None
        return Subscription.model_validate(obj)

    async def list_subscriptions(self, query: ListSubscriptionsQuery) -> list[Subscription]:
        db_query = self._session.query(SubscriptionORM)
        if query.user_id is not None:
            db_query = db_query.filter(SubscriptionORM.user_id == query.user_id)
        rows = db_query.all()
        return [Subscription.model_validate(row) for row in rows]

    async def list_expired_active_subscriptions(self) -> list[Subscription]:
        from datetime import UTC, datetime

        from vpn_core.subscription_domain.domain.subscription import SubscriptionStatus

        now = datetime.now(UTC)
        rows = (
            self._session.query(SubscriptionORM)
            .filter(
                SubscriptionORM.status == SubscriptionStatus.active,
                SubscriptionORM.expire_at <= now,
            )
            .all()
        )
        return [Subscription.model_validate(row) for row in rows]

    async def update_subscription(self, subscription: Subscription) -> Subscription | None:
        obj = self._session.get(SubscriptionORM, subscription.id)
        if not obj:
            return None

        obj.status = subscription.status
        obj.traffic_used_bytes = subscription.traffic_used_bytes
        obj.traffic_limit_bytes = subscription.traffic_limit_bytes
        obj.expire_at = subscription.expire_at
        obj.plan_id = subscription.plan_id

        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return Subscription.model_validate(obj)

    async def create_traffic_usage(self, traffic: TrafficUsage) -> TrafficUsage:
        obj = TrafficUsageORM(
            subscription_id=traffic.subscription_id,
            server_id=traffic.server_id,
            uuid=traffic.uuid,
            upload_bytes=traffic.upload_bytes,
            download_bytes=traffic.download_bytes,
            total_bytes=traffic.total_bytes,
            interval_seconds=traffic.interval_seconds,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return TrafficUsage.model_validate(obj)

    async def list_traffic_usages(self, query: ListTrafficUsagesQuery) -> list[TrafficUsage]:
        rows = (
            self._session.query(TrafficUsageORM)
            .filter(TrafficUsageORM.subscription_id == query.subscription_id)
            .all()
        )
        return [TrafficUsage.model_validate(row) for row in rows]
