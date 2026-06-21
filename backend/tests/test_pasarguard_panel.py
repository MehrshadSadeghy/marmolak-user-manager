import pytest

from vpn_core.pasarguard_panel_domain.utils.token import parse_subscription_token


def test_parse_subscription_token_from_url():
    assert parse_subscription_token("https://panel.example.com/sub/abc123") == "abc123"


def test_parse_subscription_token_from_start_payload():
    assert parse_subscription_token("/start abc123") == "abc123"


def test_parse_subscription_token_plain():
    assert parse_subscription_token("token-only") == "token-only"
