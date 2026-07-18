from typing import Annotated

from fastapi import APIRouter, HTTPException, Path

from vpn_core.v2ray_sync.api.v1.dependency import V2RayProvisioningServiceDep
from vpn_core.v2ray_sync.api.v1.dto import (
    DeactivateV2RayDTO,
    DeactivateV2RayResponseDTO,
    ProvisionV2RayDTO,
    ProvisionV2RayResponseDTO,
    V2RayConfigListResponseDTO,
    V2RayCredentialDTO,
)

router = APIRouter(
    prefix="/api/v1/v2ray",
    tags=["v2ray"],
)


@router.post("/provision", response_model=ProvisionV2RayResponseDTO)
async def provision_v2ray(
    body: ProvisionV2RayDTO,
    service: V2RayProvisioningServiceDep,
) -> ProvisionV2RayResponseDTO:
    result = await service.provision(body.to_command())
    return ProvisionV2RayResponseDTO(
        configs=[V2RayCredentialDTO.from_domain(c) for c in result.credentials],
        results=result.results,
        idempotent=result.idempotent,
    )


@router.get("/users/{user_id}/configs", response_model=V2RayConfigListResponseDTO)
async def list_user_configs(
    user_id: Annotated[int, Path()],
    service: V2RayProvisioningServiceDep,
) -> V2RayConfigListResponseDTO:
    configs = await service.list_configs(user_id)
    return V2RayConfigListResponseDTO(
        configs=[V2RayCredentialDTO.from_domain(c) for c in configs]
    )


@router.post("/deactivate", response_model=DeactivateV2RayResponseDTO)
async def deactivate_v2ray(
    body: DeactivateV2RayDTO,
    service: V2RayProvisioningServiceDep,
) -> DeactivateV2RayResponseDTO:
    count = await service.deactivate(body.to_command())
    return DeactivateV2RayResponseDTO(revoked_count=count, reason=body.reason)
