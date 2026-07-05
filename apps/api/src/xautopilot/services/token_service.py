from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel

from xautopilot.config import settings

ALGORITHM = "HS256"


class TokenPayload(BaseModel):
    sub: str
    exp: datetime


def create_access_token(user_id: UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> UUID:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return UUID(payload["sub"])
    except (JWTError, KeyError, ValueError) as exc:
        raise ValueError("Invalid token") from exc
