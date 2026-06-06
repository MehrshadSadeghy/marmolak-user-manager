from typing import Annotated

from fastapi import Depends, Request

from vpn_core.billing_domain.service import BillingService
from vpn_core.common.db.dependencies import DbSessionDep


def get_billing_service(request: Request, session: DbSessionDep) -> BillingService:
    return request.app.state.container.build_billing_service(session)


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]
