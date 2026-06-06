from typing import Annotated

from fastapi import Depends, Request

from vpn_core.commerce_domain.service import CommerceService


def get_commerce_service(request: Request) -> CommerceService:
    return request.app.state.container.get_commerce_service()


CommerceServiceDep = Annotated[CommerceService, Depends(get_commerce_service)]
