"""Production config checks — run at API startup."""

from cryptography.fernet import Fernet

from xautopilot.config import Settings

DEV_SECRET_KEY = "dev-secret-change-in-production"
MIN_SECRET_KEY_LENGTH = 32


def _is_valid_fernet_key(value: str) -> bool:
    try:
        Fernet(value.encode())
        return True
    except (ValueError, TypeError):
        return False


def validate_settings(config: Settings) -> list[str]:
    """Return human-readable config issues. Empty list means OK for this environment."""
    issues: list[str] = []

    if config.app_env in ("staging", "production"):
        if config.secret_key == DEV_SECRET_KEY:
            issues.append("SECRET_KEY is still the dev default")
        if len(config.secret_key) < MIN_SECRET_KEY_LENGTH:
            issues.append(f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters")

    if config.app_env in ("staging", "production"):
        if not config.token_encryption_key:
            issues.append("TOKEN_ENCRYPTION_KEY is required in staging/production")
        elif config.token_encryption_key == config.secret_key:
            issues.append("TOKEN_ENCRYPTION_KEY must differ from SECRET_KEY")
        elif not _is_valid_fernet_key(config.token_encryption_key):
            issues.append(
                "TOKEN_ENCRYPTION_KEY must be a Fernet key "
                "(run scripts/generate-secrets.sh)"
            )

    if config.app_env == "production":
        if config.x_api_mode != "live":
            issues.append("X_API_MODE must be 'live' in production")
        if config.llm_mode != "live":
            issues.append("LLM_MODE must be 'live' in production")
        if not config.openai_api_key:
            issues.append("OPENAI_API_KEY is required in production")

        for origin in config.cors_origins:
            if not origin.startswith("https://"):
                issues.append(f"CORS origin must use HTTPS in production: {origin}")
            if "localhost" in origin or "127.0.0.1" in origin:
                issues.append(f"CORS origin must not be localhost in production: {origin}")

        if config.frontend_url.startswith("http://"):
            issues.append("FRONTEND_URL must use HTTPS in production")
        if config.x_redirect_uri.startswith("http://"):
            issues.append("X_REDIRECT_URI must use HTTPS in production")

    return issues


def secrets_configured(config: Settings) -> bool:
    return len(validate_settings(config)) == 0
