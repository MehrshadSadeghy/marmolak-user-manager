from abc import ABC, abstractmethod

from vpn_core.pasarguard_panel_domain.domain.panel_link import PasarguardPanelLink


class PasarguardPanelLinkRepository(ABC):
    @abstractmethod
    async def get_by_user_id(self, user_id: int) -> PasarguardPanelLink | None:
        raise NotImplementedError

    @abstractmethod
    async def upsert(self, link: PasarguardPanelLink) -> PasarguardPanelLink:
        raise NotImplementedError
