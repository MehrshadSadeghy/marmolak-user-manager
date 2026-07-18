from typing import Annotated

from fastapi import Depends, Request

from vpn_core.client_subscription_domain.service import ClientSubscriptionService
from vpn_core.common.db.dependencies import DbSessionDep


def get_client_subscription_service(
    request: Request,
    session: DbSessionDep,
) -> ClientSubscriptionService:
    return request.app.state.container.build_client_subscription_service(session)


ClientSubscriptionServiceDep = Annotated[
    ClientSubscriptionService, Depends(get_client_subscription_service)
]
