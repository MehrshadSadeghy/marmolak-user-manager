from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Response

from vpn_core.client_subscription_domain.api.v1.dependency import ClientSubscriptionServiceDep

router = APIRouter(tags=["client-subscription"])


@router.get("/sub/{token}")
async def get_client_subscription(
    token: Annotated[str, Path(min_length=8, max_length=128)],
    service: ClientSubscriptionServiceDep,
) -> Response:
    try:
        feed = await service.render_subscription_feed(token)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to render subscription") from exc
    return Response(content=feed.body, media_type="text/plain; charset=utf-8", headers=feed.headers)
