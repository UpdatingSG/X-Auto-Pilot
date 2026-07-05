import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from xautopilot.config import settings


class TokenDecryptionError(Exception):
    """Raised when stored tokens cannot be decrypted (e.g. after key rotation)."""


def _dev_derived_fernet() -> Fernet:
    digest = hashlib.sha256(settings.secret_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def _fernet() -> Fernet:
    if settings.token_encryption_key:
        return Fernet(settings.token_encryption_key.encode())
    if settings.app_env == "development":
        return _dev_derived_fernet()
    raise RuntimeError(
        "TOKEN_ENCRYPTION_KEY is required outside development. "
        "Run scripts/generate-secrets.sh and set it in apps/api/.env"
    )


def encryption_key_source() -> str:
    if settings.token_encryption_key:
        return "token_encryption_key"
    return "secret_key_derived_dev_only"


def encrypt_text(value: str) -> bytes:
    return _fernet().encrypt(value.encode())


def decrypt_text(value: bytes) -> str:
    try:
        return _fernet().decrypt(value).decode()
    except InvalidToken as exc:
        raise TokenDecryptionError(
            "Cannot decrypt stored token. If you changed TOKEN_ENCRYPTION_KEY, "
            "disconnect and reconnect your X account."
        ) from exc
