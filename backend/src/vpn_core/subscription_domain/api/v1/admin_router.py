from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from vpn_core.common.auth.bot_api_key import verify_admin_telegram_id, verify_bot_api_key
from vpn_core.subscription_domain.api.v1.dependency import SubscriptionServiceDep
from vpn_core.subscription_domain.api.v1.dto import (
    CreatePlanDTO,
    PlanListResponseDTO,
    PlanResponseDTO,
    UpdatePlanDTO,
)

router = APIRouter(
    prefix="/api/v1/admin/subscription",
    tags=["admin-subscription"],
    dependencies=[Depends(verify_bot_api_key), Depends(verify_admin_telegram_id)],
)


@router.get("/plans", response_model=PlanListResponseDTO)
async def list_plans(service: SubscriptionServiceDep) -> PlanListResponseDTO:
    plans = await service.list_plans()
    return PlanListResponseDTO(plans=plans)


@router.post("/plans", response_model=PlanResponseDTO)
async def create_plan(body: CreatePlanDTO, service: SubscriptionServiceDep) -> PlanResponseDTO:
    plan = await service.create_plan(body.to_domain())
    return PlanResponseDTO(plan=plan)


@router.patch("/plans/{plan_id}", response_model=PlanResponseDTO)
async def update_plan(
    plan_id: Annotated[int, Path()],
    body: UpdatePlanDTO,
    service: SubscriptionServiceDep,
) -> PlanResponseDTO:
    existing = await service.get_plan(body.to_get_query(plan_id))
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    updated_plan = body.apply(existing)
    updated = await service.update_plan(updated_plan)
    if not updated:
        raise HTTPException(status_code=404, detail="Plan not found")
    return PlanResponseDTO(plan=updated)


@router.delete("/plans/{plan_id}")
async def delete_plan(plan_id: Annotated[int, Path()], service: SubscriptionServiceDep) -> dict:
    if not await service.delete_plan(plan_id):
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"deleted": True}
