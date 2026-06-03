from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Path

from vpn_core.openvpn_sync.api.v1.dependency import OpenVpnProvisioningServiceDep, OpenVpnTrafficServiceDep
from vpn_core.openvpn_sync.api.v1.dto import (
    DeactivateOpenVpnDTO,
    DeactivateOpenVpnResponseDTO,
    OpenVpnConfigListResponseDTO,
    OpenVpnCredentialDTO,
    ProvisionOpenVpnDTO,
    ProvisionOpenVpnResponseDTO,
    ReportTrafficDTO,
    TrafficReportResponseDTO,
)

router = APIRouter(
    prefix="/api/v1/openvpn",
    tags=["openvpn"],
)


@router.post("/provision", response_model=ProvisionOpenVpnResponseDTO)
async def provision_openvpn(
    body: ProvisionOpenVpnDTO,
    service: OpenVpnProvisioningServiceDep,
) -> ProvisionOpenVpnResponseDTO:
    """Purchase / create OpenVPN account(s) on a registered server via vpn-node."""
    result = await service.provision(body.to_command())
    return ProvisionOpenVpnResponseDTO(
        configs=[OpenVpnCredentialDTO.from_domain(c) for c in result.credentials],
        results=result.results,
        idempotent=result.idempotent,
    )


@router.get("/users/{user_id}/configs", response_model=OpenVpnConfigListResponseDTO)
async def list_user_configs(
    user_id: Annotated[int, Path()],
    service: OpenVpnProvisioningServiceDep,
    server_id: Annotated[int | None, Query()] = None,
) -> OpenVpnConfigListResponseDTO:
    configs = await service.list_configs(user_id, server_id=server_id)
    return OpenVpnConfigListResponseDTO(
        configs=[OpenVpnCredentialDTO.from_domain(c) for c in configs]
    )


@router.get("/configs/{config_id}", response_model=OpenVpnCredentialDTO)
async def get_config(
    config_id: Annotated[int, Path()],
    service: OpenVpnProvisioningServiceDep,
) -> OpenVpnCredentialDTO:
    config = await service.get_config(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return OpenVpnCredentialDTO.from_domain(config)


@router.post("/deactivate", response_model=DeactivateOpenVpnResponseDTO)
async def deactivate_openvpn(
    body: DeactivateOpenVpnDTO,
    service: OpenVpnProvisioningServiceDep,
) -> DeactivateOpenVpnResponseDTO:
    count = await service.deactivate(body.to_command())
    return DeactivateOpenVpnResponseDTO(revoked_count=count, reason=body.reason)


@router.post("/traffic/report", response_model=TrafficReportResponseDTO)
async def report_traffic(
    body: ReportTrafficDTO,
    traffic_service: OpenVpnTrafficServiceDep,
) -> TrafficReportResponseDTO:
    recorded = await traffic_service.report_usage(body.to_command())
    total = await traffic_service.get_usage_total(
        body.user_id, subscription_id=body.subscription_id
    )
    return TrafficReportResponseDTO(
        user_id=body.user_id,
        bytes_used=recorded.bytes_used,
        total_bytes=total,
    )
