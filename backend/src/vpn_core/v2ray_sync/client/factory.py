from vpn_core.v2ray_sync.client.http_client import HttpV2RayClient


class V2RayClientFactory:
    @staticmethod
    def create() -> HttpV2RayClient:
        return HttpV2RayClient()
