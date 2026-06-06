from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from vpn_core.commerce_domain.api.v1.dependency import CommerceServiceDep
from vpn_core.commerce_domain.api.v1.dto import (
    BotSettingsResponseDTO,
    CreateServiceTypeDTO,
    ServiceTypeListResponseDTO,
    ServiceTypeResponseDTO,
    UpdateBotSettingsDTO,
    UpdateServiceTypeDTO,
)
from vpn_core.common.auth.bot_api_key import verify_admin_telegram_id, verify_bot_api_key

router = APIRouter(
    prefix="/api/v1/admin/commerce",
    tags=["admin-commerce"],
    dependencies=[Depends(verify_bot_api_key), Depends(verify_admin_telegram_id)],
)


@router.get("/service-types", response_model=ServiceTypeListResponseDTO)
async def list_service_types(service: CommerceServiceDep) -> ServiceTypeListResponseDTO:
    return ServiceTypeListResponseDTO(service_types=await service.list_service_types())


@router.post("/service-types", response_model=ServiceTypeResponseDTO)
async def create_service_type(
    body: CreateServiceTypeDTO,
    service: CommerceServiceDep,
) -> ServiceTypeResponseDTO:
    created = await service.create_service_type(body.to_domain())
    return ServiceTypeResponseDTO(service_type=created)


@router.patch("/service-types/{slug}", response_model=ServiceTypeResponseDTO)
async def update_service_type(
    slug: Annotated[str, Path()],
    body: UpdateServiceTypeDTO,
    service: CommerceServiceDep,
) -> ServiceTypeResponseDTO:
    existing = await service.get_service_type(slug)
    if not existing:
        raise HTTPException(status_code=404, detail="Service type not found")
    if body.display_name is not None:
        existing.display_name = body.display_name
    if body.description is not None:
        existing.description = body.description
    if body.is_enabled is not None:
        existing.is_enabled = body.is_enabled
    if body.sort_order is not None:
        existing.sort_order = body.sort_order
    updated = await service.update_service_type(existing)
    if not updated:
        raise HTTPException(status_code=404, detail="Service type not found")
    return ServiceTypeResponseDTO(service_type=updated)


@router.post("/service-types/{slug}/enable", response_model=ServiceTypeResponseDTO)
async def enable_service_type(
    slug: Annotated[str, Path()],
    service: CommerceServiceDep,
) -> ServiceTypeResponseDTO:
    updated = await service.set_service_type_enabled(slug, True)
    if not updated:
        raise HTTPException(status_code=404, detail="Service type not found")
    return ServiceTypeResponseDTO(service_type=updated)


@router.post("/service-types/{slug}/disable", response_model=ServiceTypeResponseDTO)
async def disable_service_type(
    slug: Annotated[str, Path()],
    service: CommerceServiceDep,
) -> ServiceTypeResponseDTO:
    updated = await service.set_service_type_enabled(slug, False)
    if not updated:
        raise HTTPException(status_code=404, detail="Service type not found")
    return ServiceTypeResponseDTO(service_type=updated)


@router.get("/bot-settings", response_model=BotSettingsResponseDTO)
async def get_bot_settings(service: CommerceServiceDep) -> BotSettingsResponseDTO:
    return BotSettingsResponseDTO(settings=await service.get_bot_settings())


@router.patch("/bot-settings", response_model=BotSettingsResponseDTO)
async def update_bot_settings(
    body: UpdateBotSettingsDTO,
    service: CommerceServiceDep,
) -> BotSettingsResponseDTO:
    settings = await service.get_bot_settings()
    if body.support_username is not None:
        settings.support_username = body.support_username
    if body.payment_instructions is not None:
        settings.payment_instructions = body.payment_instructions
    updated = await service.update_bot_settings(settings)
    return BotSettingsResponseDTO(settings=updated)
