from typing import Annotated

from fastapi import Depends, Request

from vpn_core.server_management_domain.service import ServerService


def get_server_service(request: Request) -> ServerService:
    container = request.app.state.container
    return container.get_server_service()


ServerServiceDep = Annotated[ServerService, Depends(get_server_service)]
