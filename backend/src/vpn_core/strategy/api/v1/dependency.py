from typing import Annotated

from fastapi import Depends, Request

from vpn_core.common.db.dependencies import DbSessionDep
from vpn_core.strategy.service import StrategyService


def get_strategy_service(request: Request, session: DbSessionDep) -> StrategyService:
    return request.app.state.container.build_strategy_service(session)


StrategyServiceDep = Annotated[StrategyService, Depends(get_strategy_service)]
