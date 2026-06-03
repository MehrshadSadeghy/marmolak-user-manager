from vpn_core.openvpn_sync.client.base import OpenVpnClient
from vpn_core.openvpn_sync.client.http_client import HttpOpenVpnClient


class OpenVpnClientFactory:
    @staticmethod
    def create() -> OpenVpnClient:
        return HttpOpenVpnClient()
