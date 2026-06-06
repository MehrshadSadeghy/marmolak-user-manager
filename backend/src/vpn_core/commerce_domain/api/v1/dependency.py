from typing import Annotated

from fastapi import Depends, Request

from vpn_core.commerce_domain.service import CommerceService
from vpn_core.common.db.dependencies import DbSessionDep


def get_commerce_service(request: Request, session: DbSessionDep) -> CommerceService:
    return request.app.state.container.build_commerce_service(session)


CommerceServiceDep = Annotated[CommerceService, Depends(get_commerce_service)]
