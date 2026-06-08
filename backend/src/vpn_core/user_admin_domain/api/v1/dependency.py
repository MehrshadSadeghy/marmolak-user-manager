from typing import Annotated

from fastapi import Depends, Request

from vpn_core.common.db.dependencies import DbSessionDep
from vpn_core.user_admin_domain.service import UserAdminService


def get_user_admin_service(request: Request, session: DbSessionDep) -> UserAdminService:
    return request.app.state.container.build_user_admin_service(session)


UserAdminServiceDep = Annotated[UserAdminService, Depends(get_user_admin_service)]
