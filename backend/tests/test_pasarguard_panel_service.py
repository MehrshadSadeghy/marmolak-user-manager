from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException

from vpn_core.pasarguard_panel_domain.service import PasarguardPanelConfig, PasarguardPanelService


@pytest.mark.asyncio
async def test_connect_user_panel_stores_link_and_formats_info():
    repository = AsyncMock()
    repository.upsert = AsyncMock(side_effect=lambda link: link)

    service = PasarguardPanelService(
        repository=repository,
        config=PasarguardPanelConfig(
            panel_base_url="https://panel.example.com",
            subscription_path="sub",
            webapp_url="https://panel.example.com",
        ),
    )

    response = httpx.Response(
        200,
        json={
            "username": "alice",
            "status": "active",
            "data_limit": 1073741824,
            "used_traffic": 1048576,
            "expire": "2030-01-01T00:00:00+00:00",
        },
        request=httpx.Request("GET", "https://panel.example.com/sub/token/info"),
    )

    async def fake_get(url: str):
        if url.endswith("/apps"):
            return httpx.Response(
                200,
                json=[
                    {
                        "name": "V2rayNG",
                        "import_url": "v2rayng://install-config?url={url}",
                        "recommended": True,
                        "platform": "android",
                    }
                ],
                request=httpx.Request("GET", url),
            )
        return response

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=fake_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    service._client = MagicMock(return_value=MagicMock(
        subscription_url=lambda token: f"https://panel.example.com/sub/{token}",
        get_subscription_info=AsyncMock(return_value=response.json()),
        get_subscription_apps=AsyncMock(return_value=[
            {
                "name": "V2rayNG",
                "import_url": "v2rayng://install-config?url={url}",
                "recommended": True,
                "platform": "android",
            }
        ]),
    ))

    result = await service.connect_user_panel(42, "https://panel.example.com/sub/token")

    assert result["info"]["username"] == "alice"
    assert result["apps"][0]["import_url"].startswith("v2rayng://")
    repository.upsert.assert_awaited_once()


@pytest.mark.asyncio
async def test_connect_user_panel_requires_configuration():
    service = PasarguardPanelService(
        repository=AsyncMock(),
        config=PasarguardPanelConfig(panel_base_url="", subscription_path="sub", webapp_url=None),
    )
    with pytest.raises(HTTPException) as exc:
        await service.connect_user_panel(1, "token")
    assert exc.value.status_code == 503
