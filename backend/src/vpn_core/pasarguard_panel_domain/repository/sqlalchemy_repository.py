from sqlalchemy.orm import Session

from vpn_core.pasarguard_panel_domain.db_model.panel_link import PasarguardPanelLinkORM
from vpn_core.pasarguard_panel_domain.domain.panel_link import PasarguardPanelLink
from vpn_core.pasarguard_panel_domain.repository.base import PasarguardPanelLinkRepository


class PasarguardPanelLinkDBRepository(PasarguardPanelLinkRepository):
    def __init__(self, session: Session):
        self._session = session

    async def get_by_user_id(self, user_id: int) -> PasarguardPanelLink | None:
        row = (
            self._session.query(PasarguardPanelLinkORM)
            .filter(PasarguardPanelLinkORM.user_id == user_id)
            .one_or_none()
        )
        return PasarguardPanelLink.model_validate(row) if row else None

    async def upsert(self, link: PasarguardPanelLink) -> PasarguardPanelLink:
        row = (
            self._session.query(PasarguardPanelLinkORM)
            .filter(PasarguardPanelLinkORM.user_id == link.user_id)
            .one_or_none()
        )
        if row is None:
            row = PasarguardPanelLinkORM(
                user_id=link.user_id,
                subscription_token=link.subscription_token,
                panel_username=link.panel_username,
                subscription_url=link.subscription_url,
            )
            self._session.add(row)
        else:
            row.subscription_token = link.subscription_token
            row.panel_username = link.panel_username
            row.subscription_url = link.subscription_url
        self._session.commit()
        self._session.refresh(row)
        return PasarguardPanelLink.model_validate(row)
