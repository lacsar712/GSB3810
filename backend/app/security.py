from datetime import UTC, datetime, timedelta
import hashlib

import jwt

from app.config import settings


ALGORITHM = "HS256"


def hash_password(raw_password: str) -> str:
    payload = f"{raw_password}:{settings.secret_key}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_password(raw_password: str, hashed_password: str) -> bool:
    return hash_password(raw_password) == hashed_password


def create_access_token(user_id: int, role: str) -> str:
    expire = datetime.now(tz=UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, str] | None:
    try:
        decoded = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        subject = decoded.get("sub")
        role = decoded.get("role")
        if subject is None or role is None:
            return None
        return {"user_id": str(subject), "role": str(role)}
    except (jwt.InvalidTokenError, ValueError):
        return None


def fake_wechat_openid(code: str) -> str:
    return "wx_" + hashlib.sha256(code.encode("utf-8")).hexdigest()[:24]
