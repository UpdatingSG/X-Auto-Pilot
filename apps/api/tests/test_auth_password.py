from xautopilot.services.auth_service import (
    BCRYPT_ROUNDS,
    hash_password,
    password_needs_rehash,
    upgrade_password_hash,
    verify_password,
)


def test_password_needs_rehash_detects_high_round_hashes():
    strong_hash = hash_password("securepass123")
    assert not password_needs_rehash(strong_hash)

    legacy_hash = bcrypt_legacy_hash(rounds=12)
    assert password_needs_rehash(legacy_hash)


def bcrypt_legacy_hash(*, rounds: int) -> str:
    import bcrypt

    return bcrypt.hashpw(b"securepass123", bcrypt.gensalt(rounds=rounds)).decode()


async def test_upgrade_password_hash_rewrites_legacy_rounds():
    from unittest.mock import AsyncMock

    from xautopilot.models.user import User

    user = User(email="legacy@example.com", password_hash=bcrypt_legacy_hash(rounds=12))
    session = AsyncMock()
    await upgrade_password_hash(session, user, "securepass123")

    assert int(user.password_hash.split("$")[2]) == BCRYPT_ROUNDS
    assert verify_password("securepass123", user.password_hash)
    session.commit.assert_awaited_once()
