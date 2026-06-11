from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from vpn_core.openvpn_sync.services.server_capacity_service import ServerCapacityService
from vpn_core.server_management_domain.domain.capacity import ServerCapacity
from vpn_core.server_management_domain.domain.connection_info import ConnectionInfo
from vpn_core.server_management_domain.domain.openvpn_settings import OpenVpnSettings
from vpn_core.server_management_domain.domain.resource_monitoring import ResourceMonitoring
from vpn_core.server_management_domain.domain.server import Server, ServerStatus


def _server(*, server_id: int = 1, max_users: int = 100) -> Server:
    return Server(
        id=server_id,
        name="test-server",
        country_code="DE",
        cpu_cores=2,
        ram_mb=2048,
        disk_gb=40,
        connection=ConnectionInfo(host="1.2.3.4", api_port=8080),
        capacity=ServerCapacity(max_users=max_users, max_bandwidth_mbps=1000),
        monitoring=ResourceMonitoring(),
        openvpn=OpenVpnSettings(enabled=True),
        status=ServerStatus.online,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_server_capacity_snapshot_marks_full_server():
    credential_repository = AsyncMock()
    credential_repository.count_active_by_server.return_value = 100
    server_service = AsyncMock()

    service = ServerCapacityService(
        credential_repository=credential_repository,
        server_service=server_service,
    )

    snapshot = await service.get_server_capacity_snapshot(_server(max_users=100))

    assert snapshot.current_users == 100
    assert snapshot.is_full is True
    assert snapshot.remaining_slots == 0


@pytest.mark.asyncio
async def test_assert_server_has_capacity_rejects_full_server():
    credential_repository = AsyncMock()
    credential_repository.count_active_by_server.return_value = 100
    server_service = AsyncMock()
    server_service.get_server.return_value = _server(max_users=100)

    service = ServerCapacityService(
        credential_repository=credential_repository,
        server_service=server_service,
    )

    with pytest.raises(HTTPException) as exc:
        await service.assert_server_has_capacity(1)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Server is at full capacity"


@pytest.mark.asyncio
async def test_sync_current_users_updates_server_record():
    credential_repository = AsyncMock()
    credential_repository.count_active_by_server.return_value = 42
    server_service = AsyncMock()
    server = _server(max_users=100)
    server_service.get_server.return_value = server

    service = ServerCapacityService(
        credential_repository=credential_repository,
        server_service=server_service,
    )

    await service.sync_current_users(1)

    assert server.capacity.current_users == 42
    server_service.update_server.assert_awaited_once_with(server)


def test_server_capacity_helpers():
    capacity = ServerCapacity(max_users=100, current_users=75, max_bandwidth_mbps=1000)

    assert capacity.is_full() is False
    assert capacity.remaining_slots() == 25

    full = ServerCapacity(max_users=100, current_users=100, max_bandwidth_mbps=1000)
    assert full.is_full() is True
    assert full.remaining_slots() == 0
