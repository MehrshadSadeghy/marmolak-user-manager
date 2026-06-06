from typing import Annotated

from fastapi import Depends, Request

from vpn_core.bot_gateway_domain.service import BotGatewayService
from vpn_core.common.db.dependencies import DbSessionDep


def get_bot_gateway_service(request: Request, session: DbSessionDep) -> BotGatewayService:
    return request.app.state.container.build_bot_gateway_service(session)


BotGatewayServiceDep = Annotated[BotGatewayService, Depends(get_bot_gateway_service)]
