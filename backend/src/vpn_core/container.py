import os
from functools import lru_cache

from vpn_core.common.db.sqlalchemy_base import Base
from vpn_core.config import APIConfig, Config, DatabaseConfig
from vpn_core.core.db.postgres import Postgres
from vpn_core.core.manager.api_manager import APIManager
from vpn_core.core.manager.base import Manager
from vpn_core.core.manager.db_manager import PostgresManager
from vpn_core.openvpn_sync.api.v1.router import router as openvpn_router
from vpn_core.openvpn_sync.repository.base import (
    OpenVpnCredentialRepository,
    OpenVpnTrafficRepository,
)
from vpn_core.openvpn_sync.repository.sqlalchemy_repository import (
    OpenVpnCredentialDBRepository,
    OpenVpnTrafficDBRepository,
)
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.openvpn_traffic_service import OpenVpnTrafficService
from vpn_core.server_management_domain.api.v1.router import router as server_router
from vpn_core.server_management_domain.repository.base import ServerRepository
from vpn_core.server_management_domain.repository.sqlalchemy_repository import (
    ServerDBRepository,
)
from vpn_core.server_management_domain.service import ServerService
from vpn_core.strategy.api.v1.router import router as strategy_router
from vpn_core.strategy.repository.base import StrategyRepository
from vpn_core.strategy.repository.sqlalchemy_repository import StrategyDBRepository
from vpn_core.strategy.service import StrategyService
from vpn_core.subscription_domain.api.v1.router import router as subscription_router
from vpn_core.subscription_domain.repository.base import SubscriptionRepository
from vpn_core.subscription_domain.repository.sqlalchemy_repository import (
    SubscriptionDBRepository,
)
from vpn_core.subscription_domain.service import SubscriptionService

import vpn_core.openvpn_sync.db_model  # noqa: F401
import vpn_core.server_management_domain.db_model  # noqa: F401
import vpn_core.subscription_domain.db_model  # noqa: F401
import vpn_core.traffic_monitoring_domain.db_model  # noqa: F401

singleton = lru_cache


class AppContainer:
    @singleton
    def get_config(self) -> Config:
        environment = os.environ.get("RAYA_TRADE_ENVIRONMENT", "config")
        return Config.from_yaml(environment=environment)

    @singleton
    def get_api_config(self) -> APIConfig:
        return self.get_config().api

    @singleton
    def get_api_manager(self) -> APIManager:
        return APIManager(
            api_config=self.get_api_config(),
            container=self,
            routers=[
                strategy_router,
                subscription_router,
                server_router,
                openvpn_router,
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
        return PostgresManager(
            provider=self.get_postgres_provider(),
            base=Base,
            session_factory=self.get_pg_session,
        )

    @singleton
    def get_managers(self) -> list[Manager]:
        return [
            self.get_api_manager(),
            self.get_postgres_manager(),
        ]

    @singleton
    def get_pg_session(self):
        manager = self.get_postgres_manager()
        return manager.get_session()

    @singleton
    def get_strategy_repository(self) -> StrategyRepository:
        session = next(self.get_pg_session())
        return StrategyDBRepository(session=session)

    @singleton
    def get_strategy_service(self) -> StrategyService:
        repo = self.get_strategy_repository()
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

    @singleton
    def get_openvpn_credential_repository(self) -> OpenVpnCredentialRepository:
        session = next(self.get_pg_session())
        return OpenVpnCredentialDBRepository(session=session)

    @singleton
    def get_openvpn_traffic_repository(self) -> OpenVpnTrafficRepository:
        session = next(self.get_pg_session())
        return OpenVpnTrafficDBRepository(session=session)

    @singleton
    def get_openvpn_provisioning_service(self) -> OpenVpnProvisioningService:
        return OpenVpnProvisioningService(
            server_service=self.get_server_service(),
            subscription_repository=self.get_subscription_repository(),
            credential_repository=self.get_openvpn_credential_repository(),
        )

    @singleton
    def get_openvpn_traffic_service(self) -> OpenVpnTrafficService:
        return OpenVpnTrafficService(
            traffic_repository=self.get_openvpn_traffic_repository(),
            subscription_repository=self.get_subscription_repository(),
            provisioning_service=self.get_openvpn_provisioning_service(),
        )
