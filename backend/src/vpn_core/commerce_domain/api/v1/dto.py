from pydantic import BaseModel

from vpn_core.commerce_domain.domain.bot_settings import BotSettings
from vpn_core.commerce_domain.domain.service_type import ServiceType


class ServiceTypeResponseDTO(BaseModel):
    service_type: ServiceType


class ServiceTypeListResponseDTO(BaseModel):
    service_types: list[ServiceType]


class UpdateServiceTypeDTO(BaseModel):
    display_name: str | None = None
    description: str | None = None
    is_enabled: bool | None = None
    sort_order: int | None = None


class CreateServiceTypeDTO(BaseModel):
    slug: str
    display_name: str
    description: str = ""
    is_enabled: bool = True
    sort_order: int = 0

    def to_domain(self) -> ServiceType:
        return ServiceType(
            slug=self.slug,
            display_name=self.display_name,
            description=self.description,
            is_enabled=self.is_enabled,
            sort_order=self.sort_order,
        )


class BotSettingsResponseDTO(BaseModel):
    settings: BotSettings


class UpdateBotSettingsDTO(BaseModel):
    support_username: str | None = None
    payment_instructions: str | None = None
