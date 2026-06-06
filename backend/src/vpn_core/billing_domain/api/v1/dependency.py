from typing import Annotated

from fastapi import Depends, Request

from vpn_core.billing_domain.service import BillingService


def get_billing_service(request: Request) -> BillingService:
    return request.app.state.container.get_billing_service()


BillingServiceDep = Annotated[BillingService, Depends(get_billing_service)]
