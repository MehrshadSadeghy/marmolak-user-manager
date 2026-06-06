from abc import ABC, abstractmethod

from vpn_core.commerce_domain.domain.bot_settings import BotSettings
from vpn_core.commerce_domain.domain.service_type import ServiceType


class CommerceRepository(ABC):
    @abstractmethod
    async def list_service_types(self, enabled_only: bool = False) -> list[ServiceType]:
        pass

    @abstractmethod
    async def get_service_type(self, slug: str) -> ServiceType | None:
        pass

    @abstractmethod
    async def create_service_type(self, service_type: ServiceType) -> ServiceType:
        pass

    @abstractmethod
    async def update_service_type(self, service_type: ServiceType) -> ServiceType | None:
        pass

    @abstractmethod
    async def get_bot_settings(self) -> BotSettings:
        pass

    @abstractmethod
    async def update_bot_settings(self, settings: BotSettings) -> BotSettings:
        pass

    @abstractmethod
    async def seed_defaults(self) -> None:
        pass
