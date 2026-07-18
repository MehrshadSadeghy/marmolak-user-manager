import os
from functools import lru_cache

from sqlalchemy.orm import Session

from vpn_core.billing_domain.repository.sqlalchemy_repository import BillingDBRepository
from vpn_core.billing_domain.service import BillingService
from vpn_core.bot_gateway_domain.api.v1.router import admin_router as bot_admin_router
from vpn_core.bot_gateway_domain.api.v1.router import router as bot_router
from vpn_core.bot_gateway_domain.service import BotGatewayService
from vpn_core.client_subscription_domain.api.v1.router import router as client_subscription_router
from vpn_core.client_subscription_domain.service import (
    ClientSubscriptionConfig,
    ClientSubscriptionService,
)
from vpn_core.billing_domain.api.v1.router import router as billing_admin_router
from vpn_core.commerce_domain.api.v1.router import router as commerce_admin_router
from vpn_core.commerce_domain.repository.sqlalchemy_repository import CommerceDBRepository
from vpn_core.commerce_domain.service import CommerceService
from vpn_core.common.db.sqlalchemy_base import Base
from vpn_core.config import APIConfig, Config, DatabaseConfig
from vpn_core.core.db.postgres import Postgres
from vpn_core.core.manager.api_manager import APIManager
from vpn_core.core.manager.base import Manager
from vpn_core.core.manager.expiry_enforcement_manager import ExpiryEnforcementManager
from vpn_core.core.manager.traffic_enforcement_manager import TrafficEnforcementManager
from vpn_core.core.manager.db_manager import PostgresManager
from vpn_core.openvpn_sync.api.v1.router import router as openvpn_router
from vpn_core.v2ray_sync.api.v1.router import router as v2ray_router
from vpn_core.openvpn_sync.repository.sqlalchemy_repository import (
    OpenVpnCredentialDBRepository,
    OpenVpnTrafficDBRepository,
)
from vpn_core.openvpn_sync.services.openvpn_credential_delivery_service import (
    OpenVpnCredentialDeliveryService,
)
from vpn_core.openvpn_sync.services.openvpn_endpoint_service import OpenVpnEndpointService
from vpn_core.openvpn_sync.services.openvpn_provisioning_service import OpenVpnProvisioningService
from vpn_core.openvpn_sync.services.password_service import PasswordService
from vpn_core.openvpn_sync.services.server_capacity_service import ServerCapacityService
from vpn_core.openvpn_sync.client.factory import OpenVpnClientFactory
from vpn_core.openvpn_sync.services.openvpn_traffic_enforcement_service import (
    OpenVpnTrafficEnforcementService,
)
from vpn_core.openvpn_sync.services.subscription_expiry_enforcement_service import (
    SubscriptionExpiryEnforcementService,
)
from vpn_core.openvpn_sync.services.openvpn_traffic_service import OpenVpnTrafficService
from vpn_core.v2ray_sync.repository.sqlalchemy_repository import V2RayCredentialDBRepository
from vpn_core.v2ray_sync.services.v2ray_capacity_service import V2RayCapacityService
from vpn_core.v2ray_sync.services.v2ray_inbound_config_service import V2RayInboundConfigService
from vpn_core.v2ray_sync.services.v2ray_provisioning_service import V2RayProvisioningService
from vpn_core.pasarguard_panel_domain.repository.sqlalchemy_repository import PasarguardPanelLinkDBRepository
from vpn_core.pasarguard_panel_domain.service import PasarguardPanelService
from vpn_core.server_management_domain.api.v1.router import router as server_router
from vpn_core.server_management_domain.repository.sqlalchemy_repository import ServerDBRepository
from vpn_core.server_management_domain.service import ServerService
from vpn_core.strategy.api.v1.router import router as strategy_router
from vpn_core.strategy.repository.sqlalchemy_repository import StrategyDBRepository
from vpn_core.strategy.service import StrategyService
from vpn_core.user_admin_domain.api.v1.router import router as user_admin_router
from vpn_core.subscription_domain.api.v1.admin_router import router as subscription_admin_router
from vpn_core.subscription_domain.api.v1.router import router as subscription_router
from vpn_core.subscription_domain.repository.sqlalchemy_repository import SubscriptionDBRepository
from vpn_core.subscription_domain.service import SubscriptionService
from vpn_core.user_admin_domain.repository.sqlalchemy_repository import UserAdminDBRepository
from vpn_core.user_admin_domain.service import UserAdminService
from vpn_core.telegram_bot.config import TelegramBotConfig
from vpn_core.telegram_bot.manager import TelegramBotManager

import vpn_core.billing_domain.db_model  # noqa: F401
import vpn_core.commerce_domain.db_model  # noqa: F401
import vpn_core.openvpn_sync.db_model  # noqa: F401
import vpn_core.v2ray_sync.db_model  # noqa: F401
import vpn_core.pasarguard_panel_domain.db_model  # noqa: F401
import vpn_core.server_management_domain.db_model  # noqa: F401
import vpn_core.subscription_domain.db_model  # noqa: F401
import vpn_core.user_admin_domain.db_model  # noqa: F401
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
                client_subscription_router,
                strategy_router,
                subscription_router,
                subscription_admin_router,
                server_router,
                openvpn_router,
                v2ray_router,
                bot_router,
                bot_admin_router,
                user_admin_router,
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
    def get_traffic_enforcement_manager(self) -> TrafficEnforcementManager:
        return TrafficEnforcementManager(container=self)

    @singleton
    def get_expiry_enforcement_manager(self) -> ExpiryEnforcementManager:
        return ExpiryEnforcementManager(container=self)

    @singleton
    def get_managers(self) -> list[Manager]:
        managers: list[Manager] = [
            self.get_postgres_manager(),
            self.get_api_manager(),
            self.get_traffic_enforcement_manager(),
            self.get_expiry_enforcement_manager(),
        ]
        bot_manager = self.get_telegram_bot_manager()
        if bot_manager:
            managers.append(bot_manager)
        return managers

    def create_db_session(self) -> Session:
        return self.get_postgres_manager().create_session()

    def build_strategy_service(self, session: Session) -> StrategyService:
        return StrategyService(strategy_repository=StrategyDBRepository(session=session))

    def build_subscription_service(self, session: Session) -> SubscriptionService:
        return SubscriptionService(repository=SubscriptionDBRepository(session=session))

    def build_commerce_service(self, session: Session) -> CommerceService:
        return CommerceService(repository=CommerceDBRepository(session=session))

    def build_billing_service(self, session: Session) -> BillingService:
        return BillingService(repository=BillingDBRepository(session=session))

    def build_server_service(self, session: Session) -> ServerService:
        return ServerService(repository=ServerDBRepository(session=session))

    def build_server_capacity_service(self, session: Session) -> ServerCapacityService:
        return ServerCapacityService(
            credential_repository=OpenVpnCredentialDBRepository(session=session),
            server_service=self.build_server_service(session),
        )

    def build_v2ray_capacity_service(self, session: Session) -> V2RayCapacityService:
        return V2RayCapacityService(
            credential_repository=V2RayCredentialDBRepository(session=session),
            server_service=self.build_server_service(session),
        )

    def build_v2ray_provisioning_service(self, session: Session) -> V2RayProvisioningService:
        return V2RayProvisioningService(
            server_service=self.build_server_service(session),
            subscription_repository=SubscriptionDBRepository(session=session),
            credential_repository=V2RayCredentialDBRepository(session=session),
            capacity_service=self.build_v2ray_capacity_service(session),
        )

    def build_openvpn_provisioning_service(self, session: Session) -> OpenVpnProvisioningService:
        return OpenVpnProvisioningService(
            server_service=self.build_server_service(session),
            subscription_repository=SubscriptionDBRepository(session=session),
            credential_repository=OpenVpnCredentialDBRepository(session=session),
            capacity_service=self.build_server_capacity_service(session),
            password_service=PasswordService(),
        )

    def build_openvpn_traffic_service(self, session: Session) -> OpenVpnTrafficService:
        provisioning_service = self.build_openvpn_provisioning_service(session)
        return OpenVpnTrafficService(
            traffic_repository=OpenVpnTrafficDBRepository(session=session),
            subscription_repository=SubscriptionDBRepository(session=session),
            provisioning_service=provisioning_service,
        )

    def build_openvpn_endpoint_service(self, session: Session) -> OpenVpnEndpointService:
        return OpenVpnEndpointService(server_service=self.build_server_service(session))

    def build_v2ray_inbound_config_service(self, session: Session) -> V2RayInboundConfigService:
        return V2RayInboundConfigService(server_service=self.build_server_service(session))

    def build_user_admin_service(self, session: Session) -> UserAdminService:
        return UserAdminService(
            user_admin_repository=UserAdminDBRepository(session=session),
            subscription_repository=SubscriptionDBRepository(session=session),
            credential_repository=OpenVpnCredentialDBRepository(session=session),
            openvpn_service=self.build_openvpn_provisioning_service(session),
            server_service=self.build_server_service(session),
        )

    def build_openvpn_traffic_enforcement_service(self, session: Session) -> OpenVpnTrafficEnforcementService:
        return OpenVpnTrafficEnforcementService(
            subscription_repository=SubscriptionDBRepository(session=session),
            credential_repository=OpenVpnCredentialDBRepository(session=session),
            provisioning_service=self.build_openvpn_provisioning_service(session),
            server_service=self.build_server_service(session),
            openvpn_client=OpenVpnClientFactory.create(),
        )

    def build_subscription_expiry_enforcement_service(
        self, session: Session
    ) -> SubscriptionExpiryEnforcementService:
        return SubscriptionExpiryEnforcementService(
            subscription_repository=SubscriptionDBRepository(session=session),
            provisioning_service=self.build_openvpn_provisioning_service(session),
            v2ray_provisioning_service=self.build_v2ray_provisioning_service(session),
        )

    def build_openvpn_delivery_service(self, session: Session) -> OpenVpnCredentialDeliveryService:
        return OpenVpnCredentialDeliveryService(
            server_service=self.build_server_service(session),
        )

    def build_bot_gateway_service(self, session: Session) -> BotGatewayService:
        return BotGatewayService(
            subscription_service=self.build_subscription_service(session),
            billing_service=self.build_billing_service(session),
            commerce_service=self.build_commerce_service(session),
            openvpn_service=self.build_openvpn_provisioning_service(session),
            v2ray_service=self.build_v2ray_provisioning_service(session),
            openvpn_endpoint_service=self.build_openvpn_endpoint_service(session),
            openvpn_delivery_service=self.build_openvpn_delivery_service(session),
            server_service=self.build_server_service(session),
            capacity_service=self.build_server_capacity_service(session),
            v2ray_capacity_service=self.build_v2ray_capacity_service(session),
            user_admin_service=self.build_user_admin_service(session),
            traffic_enforcement_service=self.build_openvpn_traffic_enforcement_service(session),
            expiry_enforcement_service=self.build_subscription_expiry_enforcement_service(session),
            subscription_base_url=self.get_subscription_base_url(),
            client_subscription_service=self.build_client_subscription_service(session),
            v2ray_inbound_config_service=self.build_v2ray_inbound_config_service(session),
        )

    def build_client_subscription_service(self, session: Session) -> ClientSubscriptionService:
        return ClientSubscriptionService(
            subscription_service=self.build_subscription_service(session),
            v2ray_service=self.build_v2ray_provisioning_service(session),
            config=ClientSubscriptionConfig.from_env(self.get_subscription_base_url()),
        )

    def build_pasarguard_panel_service(self, session: Session) -> PasarguardPanelService:
        return PasarguardPanelService(
            repository=PasarguardPanelLinkDBRepository(session=session),
        )
