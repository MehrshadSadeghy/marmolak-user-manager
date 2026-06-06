from typing import Annotated

from fastapi import Depends, Request

from vpn_core.common.db.dependencies import DbSessionDep
from vpn_core.server_management_domain.service import ServerService


def get_server_service(request: Request, session: DbSessionDep) -> ServerService:
    return request.app.state.container.build_server_service(session)


ServerServiceDep = Annotated[ServerService, Depends(get_server_service)]
