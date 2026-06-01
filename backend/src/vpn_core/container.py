import os
from functools import lru_cache
from typing import Any, Coroutine

from raya_trade_app.ai_agent.agent.langchain import LangchainAgent
from raya_trade_app.ai_agent.service import AIService
from raya_trade_app.common.db.sqlalchemy_base import Base
from raya_trade_app.config import Config, APIConfig, DatabaseConfig
from raya_trade_app.core.db.postgres import Postgres
from raya_trade_app.core.manager.ai_agent_manager import AIManager
from raya_trade_app.core.manager.api_manager import APIManager
from raya_trade_app.core.manager.base import Manager
from raya_trade_app.core.manager.db_manager import PostgresManager

from raya_trade_app.strategy.api.v1.router import router as strategy_router
from raya_trade_app.ai_agent.api.v1.router import router as ai_router
from raya_trade_app.strategy.repository.base import StrategyRepository
from raya_trade_app.strategy.repository.sqlalchemy_repository import StrategyDBRepository
from raya_trade_app.strategy.service import StrategyService

import vpn_core.subscription_domain.db_model  # noqa: F401
import vpn_core.server_management_domain.db_model  # noqa: F401
import vpn_core.traffic_monitoring_domain.db_model  # noqa: F401
from vpn_core.subscription_domain.api.v1.router import router as subscription_router
from vpn_core.subscription_domain.repository.base import SubscriptionRepository
from vpn_core.subscription_domain.repository.sqlalchemy_repository import SubscriptionDBRepository
from vpn_core.subscription_domain.service import SubscriptionService
from vpn_core.server_management_domain.api.v1.router import router as server_router
from vpn_core.server_management_domain.repository.base import ServerRepository
from vpn_core.server_management_domain.repository.sqlalchemy_repository import ServerDBRepository
from vpn_core.server_management_domain.service import ServerService

singleton = lru_cache

class AppContainer:

    @singleton
    def get_config(self) -> APIConfig:
        environment = os.environ.get("RAYA_TRADE_ENVIRONMENT")
        return Config.from_yaml(environment=environment)

    @singleton
    def get_api_manager(self) -> APIManager:
        return APIManager(
            api_config=self.get_config().api,
            container=self,
            routers=[
                strategy_router,
                ai_router,
                subscription_router,
                server_router,
            ],
        )

    @singleton
    def get_db_config(self) -> DatabaseConfig:
        return self.get_config().postgres

    @singleton
    def get_postgres_provider(self) -> Postgres:
        return Postgres(self.get_db_config())


    @singleton
    def get_postgres_manager(self) -> PostgresManager:
        print("1")
        return PostgresManager(
            provider=self.get_postgres_provider(),
            base = Base,
            session_factory=self.get_pg_session,
        )

    @singleton
    def get_managers(self) -> list[Manager]:
        return [
            self.get_api_manager(),
            self.get_postgres_manager(),
            self.get_ai_manager(),
        ]

    @singleton
    def get_pg_session(self):
        manager = self.get_postgres_manager()
        print("2")
        return manager.get_session()

    @singleton
    def get_strategy_repository(self) -> StrategyRepository:
        session = next(self.get_pg_session())
        return StrategyDBRepository(session=session)

    @singleton
    def get_strategy_service(self) -> StrategyService:
        print("4")
        repo =  self.get_strategy_repository()
        return StrategyService(strategy_repository=repo)

    @singleton
    def get_subscription_repository(self) -> SubscriptionRepository:
        session = next(self.get_pg_session())
        return SubscriptionDBRepository(session=session)

    @singleton
    def get_subscription_service(self) -> SubscriptionService:
        return SubscriptionService(repository=self.get_subscription_repository())

    @singleton
    def get_server_repository(self) -> ServerRepository:
        session = next(self.get_pg_session())
        return ServerDBRepository(session=session)

    @singleton
    def get_server_service(self) -> ServerService:
        return ServerService(repository=self.get_server_repository())

    async def get_ai_service(self) -> AIService:
        agent = await self.get_ai_agent()
        return AIService(agent=agent)


    async def get_ai_agent(self) -> LangchainAgent:
        return LangchainAgent(
            model= await self.get_ai_manager().get_ai_model(),
        )

    @singleton
    def get_ai_model_config(self,):
        return self.get_config().ai

    @singleton
    def get_ai_manager(self) -> AIManager:
        return AIManager(
            model_config=self.get_ai_model_config(),
        )

