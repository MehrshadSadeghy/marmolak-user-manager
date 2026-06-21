import pytest

from vpn_core.openvpn_sync.config import (
    get_openvpn_auth_mode,
    get_provisioning_auth_mode,
    get_server_auth_mode,
    provisions_without_client_cert,
)
from vpn_core.openvpn_sync.domain.auth_mode import OpenVpnAuthMode
from vpn_core.openvpn_sync.domain.openvpn_client_credential import OpenVpnClientCredential


def test_get_openvpn_auth_mode_defaults_to_certificate(monkeypatch):
    monkeypatch.delenv("OPENVPN_AUTH_MODE", raising=False)
    assert get_openvpn_auth_mode() == OpenVpnAuthMode.certificate


def test_get_openvpn_auth_mode_reads_env(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    assert get_openvpn_auth_mode() == OpenVpnAuthMode.dual


def test_get_server_auth_mode_matches_openvpn_auth_mode(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    assert get_server_auth_mode() == OpenVpnAuthMode.dual


def test_get_provisioning_auth_mode_defaults_certificate(monkeypatch):
    monkeypatch.delenv("OPENVPN_AUTH_MODE", raising=False)
    monkeypatch.delenv("OPENVPN_PROVISIONING_AUTH_MODE", raising=False)
    assert get_provisioning_auth_mode() == OpenVpnAuthMode.certificate


def test_get_provisioning_auth_mode_rollout_dual_server_provisions_user_pass(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.delenv("OPENVPN_PROVISIONING_AUTH_MODE", raising=False)
    assert get_provisioning_auth_mode() == OpenVpnAuthMode.user_pass


def test_get_provisioning_auth_mode_explicit_override(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "dual")
    monkeypatch.setenv("OPENVPN_PROVISIONING_AUTH_MODE", "dual")
    assert get_provisioning_auth_mode() == OpenVpnAuthMode.dual


def test_get_provisioning_auth_mode_user_pass_env(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "user_pass")
    assert get_provisioning_auth_mode() == OpenVpnAuthMode.user_pass


def test_provisions_without_client_cert_only_for_user_pass():
    assert provisions_without_client_cert(OpenVpnAuthMode.user_pass) is True
    assert provisions_without_client_cert(OpenVpnAuthMode.dual) is False
    assert provisions_without_client_cert(OpenVpnAuthMode.certificate) is False


def test_get_openvpn_auth_mode_invalid_falls_back_to_certificate(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTH_MODE", "invalid-mode")
    assert get_openvpn_auth_mode() == OpenVpnAuthMode.certificate


def test_get_openvpn_auto_apply_server_auth_defaults_false(monkeypatch):
    monkeypatch.delenv("OPENVPN_AUTO_APPLY_SERVER_AUTH", raising=False)
    from vpn_core.openvpn_sync.config import get_openvpn_auto_apply_server_auth

    assert get_openvpn_auto_apply_server_auth() is False


def test_get_openvpn_auto_apply_server_auth_reads_env(monkeypatch):
    monkeypatch.setenv("OPENVPN_AUTO_APPLY_SERVER_AUTH", "true")
    from vpn_core.openvpn_sync.config import get_openvpn_auto_apply_server_auth

    assert get_openvpn_auto_apply_server_auth() is True


def test_openvpn_client_credential_auth_defaults():
    credential = OpenVpnClientCredential(
        user_id=1,
        server_id=2,
        telegram_id="123",
        common_name="0123456789",
        ovpn_content="<ca>test</ca>",
    )
    assert credential.auth_mode == OpenVpnAuthMode.certificate
    assert credential.vpn_username is None
    assert credential.password_hash is None
    assert credential.password_rotated_at is None
    assert credential.auth_synced_at is None
