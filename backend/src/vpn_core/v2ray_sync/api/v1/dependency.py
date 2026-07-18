from typing import Annotated

from fastapi import Depends, Request

from vpn_core.common.db.dependencies import DbSessionDep
from vpn_core.v2ray_sync.services.v2ray_provisioning_service import V2RayProvisioningService


def get_v2ray_provisioning_service(
    request: Request,
    session: DbSessionDep,
) -> V2RayProvisioningService:
    return request.app.state.container.build_v2ray_provisioning_service(session)


V2RayProvisioningServiceDep = Annotated[
    V2RayProvisioningService, Depends(get_v2ray_provisioning_service)
]
