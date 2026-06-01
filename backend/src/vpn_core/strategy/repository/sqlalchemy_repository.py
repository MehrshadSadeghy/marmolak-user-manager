from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from raya_trade_app.strategy.db.pg_model.strategy import StrategyORM
from raya_trade_app.strategy.db.strategy import Strategy
from raya_trade_app.strategy.repository.base import StrategyRepository


class StrategyDBRepository(StrategyRepository):
    def __init__(self, session):
        self._session = session

    async def put_strategy(self, strategy_data: Strategy) -> None:
        obj = (
            self._session.query(StrategyORM)
            .filter(StrategyORM.id == strategy_data.id)
            .first()
        )
        if not obj:
            return None

        obj.name = strategy_data.name
        obj.data = strategy_data.data

        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return None

    async def set_strategy(self, strategy_data: Strategy) -> None:
        obj = StrategyORM(
            name=strategy_data.name,
            data=strategy_data.data,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)

        return None

    async def delete_strategy(self, strategy_id: int) -> None:
        obj = self._session.query(StrategyORM).filter(StrategyORM.id == strategy_id).first()
        if not obj:
            return None

        self._session.delete(obj)
        self._session.commit()
        self._session.refresh(obj)

        return None

    async def get_strategy(self, strategy_id: UUID) -> Optional[Strategy]:
        obj = self._session.query(StrategyORM).where(StrategyORM.id == strategy_id).first()
        if not obj:
            return None
        return Strategy.from_orm(obj)

    async def get_strategies(self) -> List[Strategy]:
        rows = self._session.query(StrategyORM).all()
        return [Strategy.from_orm(r) for r in rows]
