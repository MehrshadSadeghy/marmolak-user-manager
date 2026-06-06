import os
from functools import lru_cache

from vpn_core.billing_domain.repository.base import BillingRepository
from vpn_core.billing_domain.repository.sqlalchemy_repository import BillingDBRepository
from vpn_core.billing_domain.service import BillingService
from vpn_core.bot_gateway_domain.api.v1.router import admin_router as bot_admin_router
from vpn_core.bot_gateway_domain.api.v1.router import router as bot_router
from vpn_core.bot_gateway_domain.service import BotGatewayService
from vpn_core.billing_domain.api.v1.router import router as billing_admin_router
from vpn_core.commerce_domain.api.v1.router import router as commerce_admin_router
from vpn_core.commerce_domain.repository.base import CommerceRepository
from vpn_core.commerce_domain.repository.sqlalchemy_repository import CommerceDBRepository
from vpn_core.commerce_domain.service import CommerceService
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
from vpn_core.subscription_domain.api.v1.admin_router import router as subscription_admin_router
from vpn_core.subscription_domain.api.v1.router import router as subscription_router
from vpn_core.subscription_domain.repository.base import SubscriptionRepository
from vpn_core.subscription_domain.repository.sqlalchemy_repository import (
    SubscriptionDBRepository,
)
from vpn_core.subscription_domain.service import SubscriptionService
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.manager import TelegramBotManager

import vpn_core.billing_domain.db_model  # noqa: F401
import vpn_core.commerce_domain.db_model  # noqa: F401
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
    def get_subscription_base_url(self) -> str:
        return os.getenv("SUBSCRIPTION_BASE_URL", "http://localhost:8080")

    @singleton
    def get_api_manager(self) -> APIManager:
        return APIManager(
            api_config=self.get_api_config(),
            container=self,
            routers=[
                strategy_router,
                subscription_router,
                subscription_admin_router,
                server_router,
                openvpn_router,
                bot_router,
                bot_admin_router,
                commerce_admin_router,
                billing_admin_router,
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
    def get_telegram_bot_config(self) -> TelegramBotConfig | None:
        return TelegramBotConfig.from_env()

    @singleton
    def get_telegram_bot_manager(self) -> TelegramBotManager | None:
        config = self.get_telegram_bot_config()
        if not config:
            return None
        return TelegramBotManager(config)

    @singleton
    def get_managers(self) -> list[Manager]:
        managers: list[Manager] = [
            self.get_postgres_manager(),
            self.get_api_manager(),
        ]
        bot_manager = self.get_telegram_bot_manager()
        if bot_manager:
            managers.append(bot_manager)
        return managers

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
    def get_commerce_repository(self) -> CommerceRepository:
        session = next(self.get_pg_session())
        return CommerceDBRepository(session=session)

    @singleton
    def get_commerce_service(self) -> CommerceService:
        return CommerceService(repository=self.get_commerce_repository())

    @singleton
    def get_billing_repository(self) -> BillingRepository:
        session = next(self.get_pg_session())
        return BillingDBRepository(session=session)

    @singleton
    def get_billing_service(self) -> BillingService:
        return BillingService(repository=self.get_billing_repository())

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

    @singleton
    def get_bot_gateway_service(self) -> BotGatewayService:
        return BotGatewayService(
            subscription_service=self.get_subscription_service(),
            billing_service=self.get_billing_service(),
            commerce_service=self.get_commerce_service(),
            openvpn_service=self.get_openvpn_provisioning_service(),
            server_service=self.get_server_service(),
            subscription_base_url=self.get_subscription_base_url(),
        )
