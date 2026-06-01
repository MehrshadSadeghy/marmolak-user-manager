from typing import Annotated

from fastapi import Depends, Request

from vpn_core.subscription_domain.service import SubscriptionService


def get_subscription_service(request: Request) -> SubscriptionService:
    container = request.app.state.container
    return container.get_subscription_service()

SubscriptionServiceDep = Annotated[SubscriptionService, Depends(get_subscription_service)]
