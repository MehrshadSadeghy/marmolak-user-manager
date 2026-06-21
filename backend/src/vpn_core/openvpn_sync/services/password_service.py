from __future__ import annotations

import secrets
import string

import bcrypt

_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%&*-_=+"
_DEFAULT_LENGTH = 16


class PasswordService:
    """Generates OpenVPN passwords and bcrypt hashes for secure storage."""

    def __init__(self, *, bcrypt_rounds: int = 12, password_length: int = _DEFAULT_LENGTH) -> None:
        if password_length < 12:
            raise ValueError("password_length must be at least 12")
        self._bcrypt_rounds = bcrypt_rounds
        self._password_length = password_length

    def generate_password(self) -> str:
        while True:
            password = "".join(
                secrets.choice(_PASSWORD_ALPHABET) for _ in range(self._password_length)
            )
            if (
                any(char.islower() for char in password)
                and any(char.isupper() for char in password)
                and any(char.isdigit() for char in password)
            ):
                return password

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=self._bcrypt_rounds)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
        except ValueError:
            return False
