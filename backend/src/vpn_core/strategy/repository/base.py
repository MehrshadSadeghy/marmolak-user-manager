from abc import abstractmethod, ABC
from uuid import UUID

from vpn_core.strategy.db.strategy import Strategy


class StrategyRepository(ABC):
    @abstractmethod
    async def set_strategy(self, strategy_data: Strategy) -> None:
        pass

    @abstractmethod
    async def put_strategy(self, strategy_data: Strategy) -> None:
        pass

    @abstractmethod
    async def get_strategies(self) -> list[Strategy]:
        pass

    @abstractmethod
    async def get_strategy(self, strategy_id: UUID) -> Strategy:
        pass

    @abstractmethod
    async def delete_strategy(self, strategy_id:int) -> None:
        pass