import re

import pytest

from vpn_core.openvpn_sync.services.password_service import PasswordService


@pytest.fixture
def password_service():
    return PasswordService(bcrypt_rounds=4, password_length=16)


def test_generate_password_meets_entropy_requirements(password_service: PasswordService):
    password = password_service.generate_password()
    assert len(password) == 16
    assert re.search(r"[a-z]", password)
    assert re.search(r"[A-Z]", password)
    assert re.search(r"\d", password)


def test_generate_password_is_unique_enough(password_service: PasswordService):
    passwords = {password_service.generate_password() for _ in range(50)}
    assert len(passwords) > 45


def test_hash_and_verify_password(password_service: PasswordService):
    password = password_service.generate_password()
    password_hash = password_service.hash_password(password)
    assert password_hash.startswith("$2")
    assert password_service.verify_password(password, password_hash) is True
    assert password_service.verify_password("wrong-password", password_hash) is False


def test_verify_password_rejects_invalid_hash(password_service: PasswordService):
    assert password_service.verify_password("secret", "not-a-bcrypt-hash") is False


def test_password_length_validation():
    with pytest.raises(ValueError, match="password_length"):
        PasswordService(password_length=8)
