from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Path

from vpn_core.server_management_domain.api.v1.dependency import ServerServiceDep
from vpn_core.server_management_domain.api.v1.dto import (
    CreateServerDTO,
    DeleteServerResponseDTO,
    GetServerQueryDTO,
    ListServersQueryDTO,
    ServerListResponseDTO,
    ServerResponseDTO,
    UpdateResourceMonitoringDTO,
    UpdateServerDTO,
    UpdateServerStatusDTO,
)
from vpn_core.server_management_domain.domain.server import ServerStatus

router = APIRouter(
    prefix="/api/v1/servers",
    tags=["servers"],
)


@router.post("", response_model=ServerResponseDTO)
async def create_server(
    body: CreateServerDTO,
    service: ServerServiceDep,
) -> ServerResponseDTO:
    server = await service.create_server(body.to_domain())
    return ServerResponseDTO(server=server)


@router.get("", response_model=ServerListResponseDTO)
async def list_servers(
    service: ServerServiceDep,
    country_code: Annotated[str | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
    status: Annotated[ServerStatus | None, Query()] = None,
    openvpn_enabled: Annotated[bool | None, Query()] = None,
) -> ServerListResponseDTO:
    query = ListServersQueryDTO(
        country_code=country_code,
        is_active=is_active,
        status=status,
        openvpn_enabled=openvpn_enabled,
    ).to_domain()
    servers = await service.list_servers(query)
    return ServerListResponseDTO(servers=servers)


@router.get("/{server_id}", response_model=ServerResponseDTO)
async def get_server(
    server_id: Annotated[int, Path()],
    service: ServerServiceDep,
) -> ServerResponseDTO:
    query = GetServerQueryDTO(server_id=server_id).to_domain()
    server = await service.get_server(query)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerResponseDTO(server=server)


@router.put("/{server_id}", response_model=ServerResponseDTO)
async def update_server(
    server_id: Annotated[int, Path()],
    body: UpdateServerDTO,
    service: ServerServiceDep,
) -> ServerResponseDTO:
    server = await service.update_server(body.to_domain(server_id=server_id))
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerResponseDTO(server=server)


@router.patch("/{server_id}/status", response_model=ServerResponseDTO)
async def update_server_status(
    server_id: Annotated[int, Path()],
    body: UpdateServerStatusDTO,
    service: ServerServiceDep,
) -> ServerResponseDTO:
    command = body.to_domain(server_id=server_id)
    server = await service.update_server_status(command)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerResponseDTO(server=server)


@router.patch("/{server_id}/monitoring", response_model=ServerResponseDTO)
async def update_resource_monitoring(
    server_id: Annotated[int, Path()],
    body: UpdateResourceMonitoringDTO,
    service: ServerServiceDep,
) -> ServerResponseDTO:
    command = body.to_domain(server_id=server_id)
    server = await service.update_resource_monitoring(command)
    if not server:
        raise HTTPException(status_code=404, detail="Server not found")
    return ServerResponseDTO(server=server)


@router.delete("/{server_id}", response_model=DeleteServerResponseDTO)
async def delete_server(
    server_id: Annotated[int, Path()],
    service: ServerServiceDep,
) -> DeleteServerResponseDTO:
    query = GetServerQueryDTO(server_id=server_id).to_domain()
    deleted = await service.delete_server(query)
    if not deleted:
        raise HTTPException(status_code=404, detail="Server not found")
    return DeleteServerResponseDTO(deleted=True)
