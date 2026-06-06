from typing import Annotated

from fastapi import Depends, Request

from vpn_core.common.db.dependencies import DbSessionDep
from vpn_core.subscription_domain.service import SubscriptionService


def get_subscription_service(request: Request, session: DbSessionDep) -> SubscriptionService:
    return request.app.state.container.build_subscription_service(session)


SubscriptionServiceDep = Annotated[SubscriptionService, Depends(get_subscription_service)]
