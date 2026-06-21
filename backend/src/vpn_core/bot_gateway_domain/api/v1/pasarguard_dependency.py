from typing import Annotated

from fastapi import Depends, Request

from vpn_core.pasarguard_panel_domain.service import PasarguardPanelService
from vpn_core.common.db.dependencies import DbSessionDep


def get_pasarguard_panel_service(request: Request, session: DbSessionDep) -> PasarguardPanelService:
    return request.app.state.container.build_pasarguard_panel_service(session)


PasarguardPanelServiceDep = Annotated[PasarguardPanelService, Depends(get_pasarguard_panel_service)]
