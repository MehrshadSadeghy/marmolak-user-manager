from vpn_core.commerce_domain.domain.bot_settings import BotSettings
from vpn_core.commerce_domain.domain.service_type import ServiceType
from vpn_core.commerce_domain.repository.base import CommerceRepository


class CommerceService:
    def __init__(self, repository: CommerceRepository):
        self._repository = repository

    async def ensure_defaults(self) -> None:
        await self._repository.seed_defaults()

    async def list_service_types(self, enabled_only: bool = False) -> list[ServiceType]:
        return await self._repository.list_service_types(enabled_only=enabled_only)

    async def get_service_type(self, slug: str) -> ServiceType | None:
        return await self._repository.get_service_type(slug)

    async def create_service_type(self, service_type: ServiceType) -> ServiceType:
        return await self._repository.create_service_type(service_type)

    async def update_service_type(self, service_type: ServiceType) -> ServiceType | None:
        return await self._repository.update_service_type(service_type)

    async def set_service_type_enabled(self, slug: str, enabled: bool) -> ServiceType | None:
        service_type = await self._repository.get_service_type(slug)
        if not service_type:
            return None
        service_type.is_enabled = enabled
        return await self._repository.update_service_type(service_type)

    async def get_bot_settings(self) -> BotSettings:
        return await self._repository.get_bot_settings()

    async def update_bot_settings(self, settings: BotSettings) -> BotSettings:
        return await self._repository.update_bot_settings(settings)
