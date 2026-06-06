from sqlalchemy.orm import Session

from vpn_core.commerce_domain.db_model.bot_settings import BotSettings as BotSettingsORM
from vpn_core.commerce_domain.db_model.service_type import ServiceType as ServiceTypeORM
from vpn_core.commerce_domain.domain.bot_settings import BotSettings
from vpn_core.commerce_domain.domain.service_type import ServiceType
from vpn_core.commerce_domain.repository.base import CommerceRepository

DEFAULT_SERVICE_TYPES = [
    ("v2ray", "V2Ray service", "V2Ray / Xray subscription", 1),
    ("openvpn", "OpenVPN service", "OpenVPN configuration files", 2),
]


class CommerceDBRepository(CommerceRepository):
    def __init__(self, session: Session):
        self._session = session

    async def list_service_types(self, enabled_only: bool = False) -> list[ServiceType]:
        query = self._session.query(ServiceTypeORM).order_by(ServiceTypeORM.sort_order)
        if enabled_only:
            query = query.filter(ServiceTypeORM.is_enabled.is_(True))
        return [ServiceType.model_validate(row) for row in query.all()]

    async def get_service_type(self, slug: str) -> ServiceType | None:
        row = (
            self._session.query(ServiceTypeORM)
            .filter(ServiceTypeORM.slug == slug)
            .one_or_none()
        )
        if not row:
            return None
        return ServiceType.model_validate(row)

    async def create_service_type(self, service_type: ServiceType) -> ServiceType:
        obj = ServiceTypeORM(
            slug=service_type.slug,
            display_name=service_type.display_name,
            description=service_type.description,
            is_enabled=service_type.is_enabled,
            sort_order=service_type.sort_order,
        )
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return ServiceType.model_validate(obj)

    async def update_service_type(self, service_type: ServiceType) -> ServiceType | None:
        obj = self._session.get(ServiceTypeORM, service_type.id)
        if not obj:
            return None
        obj.display_name = service_type.display_name
        obj.description = service_type.description
        obj.is_enabled = service_type.is_enabled
        obj.sort_order = service_type.sort_order
        self._session.add(obj)
        self._session.commit()
        self._session.refresh(obj)
        return ServiceType.model_validate(obj)

    async def get_bot_settings(self) -> BotSettings:
        row = self._session.query(BotSettingsORM).first()
        if row:
            return BotSettings.model_validate(row)
        row = BotSettingsORM()
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return BotSettings.model_validate(row)

    async def update_bot_settings(self, settings: BotSettings) -> BotSettings:
        row = self._session.query(BotSettingsORM).first()
        if not row:
            row = BotSettingsORM()
            self._session.add(row)
        row.support_username = settings.support_username
        row.payment_instructions = settings.payment_instructions
        self._session.commit()
        self._session.refresh(row)
        return BotSettings.model_validate(row)

    async def seed_defaults(self) -> None:
        existing = self._session.query(ServiceTypeORM).count()
        if existing:
            return
        for slug, display_name, description, sort_order in DEFAULT_SERVICE_TYPES:
            self._session.add(
                ServiceTypeORM(
                    slug=slug,
                    display_name=display_name,
                    description=description,
                    sort_order=sort_order,
                    is_enabled=True,
                )
            )
        if not self._session.query(BotSettingsORM).first():
            self._session.add(BotSettingsORM())
        self._session.commit()
