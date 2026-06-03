from uuid import UUID

from vpn_core.strategy.db.strategy import Strategy
from vpn_core.strategy.repository.base import StrategyRepository


class StrategyService:
    def __init__(self, strategy_repository: StrategyRepository):
        self._strategy_repository = strategy_repository

    async def get_strategies(self) -> list[Strategy]:
        return await self._strategy_repository.get_strategies()

    async def get_strategy(
            self,
            strategy_id: UUID
    ):
        strategy = await self._strategy_repository.get_strategy(strategy_id=strategy_id)
        return strategy

    async def create_strategy(self, strategy_data: Strategy) -> None:
        await self._strategy_repository.set_strategy(strategy_data=strategy_data)
        return None

    async def update_strategy(self, strategy_data: Strategy) -> None:
        await self._strategy_repository.put_strategy(strategy_data=strategy_data)
        return None

    async def delete_strategy(self, strategy_id: int) -> None:
        await self._strategy_repository.delete_strategy(strategy_id=strategy_id)