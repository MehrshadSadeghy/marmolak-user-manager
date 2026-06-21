from vpn_core.bot_gateway_domain.service import BotGatewayService


def test_is_valid_ovpn_accepts_auth_only_profile():
    content = "client\nauth-user-pass\n<ca>\nreal-ca\n</ca>\n"
    assert BotGatewayService._is_valid_ovpn(content) is True


def test_is_valid_ovpn_rejects_mock_ca():
    assert BotGatewayService._is_valid_ovpn("<ca>MOCK-CA</ca>") is False
