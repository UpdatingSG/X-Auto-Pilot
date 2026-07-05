"""Step 3: production secrets and config validation."""

from cryptography.fernet import Fernet

from xautopilot.config import Settings
from xautopilot.services.crypto_service import decrypt_text, encrypt_text, encryption_key_source
from xautopilot.settings_validation import (
    DEV_SECRET_KEY,
    secrets_configured,
    validate_settings,
)


def _valid_prod_settings(**overrides) -> Settings:
    key = Fernet.generate_key().decode()
    base = {
        "app_env": "production",
        "secret_key": "a" * 64,
        "token_encryption_key": key,
        "cors_origins": ["https://app.example.com"],
        "frontend_url": "https://app.example.com",
        "x_redirect_uri": "https://app.example.com/settings/x/callback",
        "x_api_mode": "live",
    }
    base.update(overrides)
    return Settings.model_validate(base)


def test_development_allows_dev_secret():
    config = Settings.model_validate({"app_env": "development", "secret_key": DEV_SECRET_KEY})
    assert validate_settings(config) == []


def test_production_rejects_dev_secret_key():
    config = _valid_prod_settings(secret_key=DEV_SECRET_KEY)
    issues = validate_settings(config)
    assert any("SECRET_KEY" in issue for issue in issues)


def test_production_requires_token_encryption_key():
    config = _valid_prod_settings(token_encryption_key="")
    issues = validate_settings(config)
    assert any("TOKEN_ENCRYPTION_KEY" in issue for issue in issues)


def test_production_rejects_http_cors():
    config = _valid_prod_settings(cors_origins=["http://localhost:3000"])
    issues = validate_settings(config)
    assert any("HTTPS" in issue for issue in issues)


def test_production_rejects_mock_x_mode():
    config = _valid_prod_settings(x_api_mode="mock")
    issues = validate_settings(config)
    assert any("X_API_MODE" in issue for issue in issues)


def test_production_requires_openai_key():
    config = _valid_prod_settings(openai_api_key="")
    issues = validate_settings(config)
    assert any("OPENAI_API_KEY" in issue for issue in issues)


def test_production_rejects_mock_llm_mode():
    config = _valid_prod_settings(llm_mode="mock", openai_api_key="sk-test")
    issues = validate_settings(config)
    assert any("LLM_MODE" in issue for issue in issues)


def test_valid_production_config_has_no_issues():
    config = _valid_prod_settings(llm_mode="live", openai_api_key="sk-test")
    assert validate_settings(config) == []
    assert secrets_configured(config) is True


def test_encrypt_decrypt_uses_token_encryption_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("xautopilot.services.crypto_service.settings.token_encryption_key", key)
    monkeypatch.setattr("xautopilot.services.crypto_service.settings.app_env", "production")

    encrypted = encrypt_text("secret-token")
    assert decrypt_text(encrypted) == "secret-token"
    assert encryption_key_source() == "token_encryption_key"


def test_dev_falls_back_to_secret_key_derivation(monkeypatch):
    monkeypatch.setattr("xautopilot.services.crypto_service.settings.token_encryption_key", "")
    monkeypatch.setattr("xautopilot.services.crypto_service.settings.app_env", "development")
    monkeypatch.setattr("xautopilot.services.crypto_service.settings.secret_key", "dev-test-key")

    encrypted = encrypt_text("dev-token")
    assert decrypt_text(encrypted) == "dev-token"
    assert encryption_key_source() == "secret_key_derived_dev_only"
