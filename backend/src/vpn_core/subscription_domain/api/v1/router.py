from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Path

from vpn_core.subscription_domain.api.v1.dependency import SubscriptionServiceDep
from vpn_core.subscription_domain.api.v1.dto import (
    CreatePlanDTO,
    CreateSubscriptionDTO,
    CreateTrafficUsageDTO,
    CreateUserDTO,
    GetPlanQueryDTO,
    GetSubscriptionQueryDTO,
    GetUserQueryDTO,
    ListSubscriptionsQueryDTO,
    ListTrafficUsagesQueryDTO,
    PlanListResponseDTO,
    PlanResponseDTO,
    SubscriptionListResponseDTO,
    SubscriptionResponseDTO,
    TrafficUsageListResponseDTO,
    TrafficUsageResponseDTO,
    UpdateSubscriptionStatusDTO,
    UserListResponseDTO,
    UserResponseDTO,
)
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Path

from vpn_core.subscription_domain.api.v1.dependency import SubscriptionServiceDep
from vpn_core.subscription_domain.api.v1.dto import (
    CreatePlanDTO,
    CreateSubscriptionDTO,
    CreateTrafficUsageDTO,
    CreateUserDTO,
    GetPlanQueryDTO,
    GetSubscriptionQueryDTO,
    GetUserQueryDTO,
    ListSubscriptionsQueryDTO,
    ListTrafficUsagesQueryDTO,
    PlanListResponseDTO,
    PlanResponseDTO,
    SubscriptionListResponseDTO,
    SubscriptionResponseDTO,
    TrafficUsageListResponseDTO,
    TrafficUsageResponseDTO,
    UpdateSubscriptionStatusDTO,
    UserListResponseDTO,
    UserResponseDTO,
)

router = APIRouter(
    prefix="/api/v1/subscription",
    tags=["subscription"],
)


@router.post("/users", response_model=UserResponseDTO)
async def create_user(
    body: CreateUserDTO,
    service: SubscriptionServiceDep,
) -> UserResponseDTO:
    user = await service.create_user(body.to_domain())
    return UserResponseDTO(user=user)


@router.get("/users", response_model=UserListResponseDTO)
async def list_users(service: SubscriptionServiceDep) -> UserListResponseDTO:
    users = await service.list_users()
    return UserListResponseDTO(users=users)


@router.get("/users/{user_id}", response_model=UserResponseDTO)
async def get_user(
    user_id: Annotated[int, Path()],
    service: SubscriptionServiceDep,
) -> UserResponseDTO:
    query = GetUserQueryDTO(user_id=user_id).to_domain()
    user = await service.get_user(query)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponseDTO(user=user)


@router.post("/plans", response_model=PlanResponseDTO)
async def create_plan(
    body: CreatePlanDTO,
    service: SubscriptionServiceDep,
) -> PlanResponseDTO:
    plan = await service.create_plan(body.to_domain())
    return PlanResponseDTO(plan=plan)


@router.get("/plans", response_model=PlanListResponseDTO)
async def list_plans(service: SubscriptionServiceDep) -> PlanListResponseDTO:
    plans = await service.list_plans()
    return PlanListResponseDTO(plans=plans)


@router.get("/plans/{plan_id}", response_model=PlanResponseDTO)
async def get_plan(
    plan_id: Annotated[int, Path()],
    service: SubscriptionServiceDep,
) -> PlanResponseDTO:
    query = GetPlanQueryDTO(plan_id=plan_id).to_domain()
    plan = await service.get_plan(query)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanResponseDTO(plan=plan)


@router.post("/subscriptions", response_model=SubscriptionResponseDTO)
async def create_subscription(
    body: CreateSubscriptionDTO,
    service: SubscriptionServiceDep,
) -> SubscriptionResponseDTO:
    subscription = await service.create_subscription(body.to_domain())
    if not subscription:
        raise HTTPException(status_code=404, detail="User or plan not found")
    return SubscriptionResponseDTO(subscription=subscription)


@router.get("/subscriptions", response_model=SubscriptionListResponseDTO)
async def list_subscriptions(
    service: SubscriptionServiceDep,
    user_id: Annotated[int | None, Query()] = None,
) -> SubscriptionListResponseDTO:
    query = ListSubscriptionsQueryDTO(user_id=user_id).to_domain()
    subscriptions = await service.list_subscriptions(query)
    return SubscriptionListResponseDTO(subscriptions=subscriptions)


@router.get("/subscriptions/{subscription_id}", response_model=SubscriptionResponseDTO)
async def get_subscription(
    subscription_id: Annotated[int, Path()],
    service: SubscriptionServiceDep,
) -> SubscriptionResponseDTO:
    query = GetSubscriptionQueryDTO(subscription_id=subscription_id).to_domain()
    subscription = await service.get_subscription(query)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return SubscriptionResponseDTO(subscription=subscription)


@router.patch(
    "/subscriptions/{subscription_id}/status",
    response_model=SubscriptionResponseDTO,
)
async def update_subscription_status(
    subscription_id: Annotated[int, Path()],
    body: UpdateSubscriptionStatusDTO,
    service: SubscriptionServiceDep,
) -> SubscriptionResponseDTO:
    command = body.to_domain(subscription_id=subscription_id)
    subscription = await service.update_subscription_status(command)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return SubscriptionResponseDTO(subscription=subscription)


@router.post("/traffic", response_model=TrafficUsageResponseDTO)
async def record_traffic_usage(
    body: CreateTrafficUsageDTO,
    service: SubscriptionServiceDep,
) -> TrafficUsageResponseDTO:
    traffic = await service.record_traffic_usage(body.to_domain())
    if not traffic:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return TrafficUsageResponseDTO(traffic_usage=traffic)


@router.get(
    "/subscriptions/{subscription_id}/traffic",
    response_model=TrafficUsageListResponseDTO,
)
async def list_traffic_usages(
    subscription_id: Annotated[int, Path()],
    service: SubscriptionServiceDep,
) -> TrafficUsageListResponseDTO:
    subscription_query = GetSubscriptionQueryDTO(subscription_id=subscription_id).to_domain()
    subscription = await service.get_subscription(subscription_query)
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")

    traffic_query = ListTrafficUsagesQueryDTO(subscription_id=subscription_id).to_domain()
    traffic_usages = await service.list_traffic_usages(traffic_query)
    return TrafficUsageListResponseDTO(traffic_usages=traffic_usages)
