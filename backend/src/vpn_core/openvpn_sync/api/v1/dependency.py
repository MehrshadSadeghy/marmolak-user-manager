from typing import Annotated

from fastapi import Depends, Request

from vpn_core.common.db.dependencies import DbSessionDep
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.openvpn_traffic_service import OpenVpnTrafficService


def get_openvpn_provisioning_service(
    request: Request,
    session: DbSessionDep,
) -> OpenVpnProvisioningService:
    return request.app.state.container.build_openvpn_provisioning_service(session)


def get_openvpn_traffic_service(
    request: Request,
    session: DbSessionDep,
) -> OpenVpnTrafficService:
    return request.app.state.container.build_openvpn_traffic_service(session)


OpenVpnProvisioningServiceDep = Annotated[
    OpenVpnProvisioningService, Depends(get_openvpn_provisioning_service)
]
OpenVpnTrafficServiceDep = Annotated[OpenVpnTrafficService, Depends(get_openvpn_traffic_service)]
