from fastapi import Request

from raya_trade_app.strategy.service import StrategyService


def get_strategy_service(
    request: Request,
) -> StrategyService:
    container = request.app.state.container
    return container.get_strategy_service()