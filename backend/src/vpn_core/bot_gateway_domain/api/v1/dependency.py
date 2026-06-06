from typing import Annotated

from fastapi import Depends, Request

from vpn_core.bot_gateway_domain.service import BotGatewayService


def get_bot_gateway_service(request: Request) -> BotGatewayService:
    return request.app.state.container.get_bot_gateway_service()


BotGatewayServiceDep = Annotated[BotGatewayService, Depends(get_bot_gateway_service)]
