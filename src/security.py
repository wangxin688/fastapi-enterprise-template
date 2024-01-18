import time
from datetime import datetime
from uuid import UUID

import jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from src.auth.schemas import AccessToken
from src.config import settings

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECS = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_TOKEN_EXPIRE_SECS = settings.REFRESH_TOKEN_EXPIRE_MINUTES * 60
PWD_CONTEXT = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.SECURITY_BCRYPT_ROUNDS,
)

API_WHITE_LISTS: set[str] = set()


class JwtTokenPayload(BaseModel):
    sub: int
    refresh: bool
    issued_at: datetime
    expires_at: datetime


def create_jwt_token(subject: int, expire_seconds: int, refresh: bool) -> tuple[str, int, int]:
    """Create jwt access token or refresh token for use

    Args:
        subject (UUID): unique ID for user(primary key used in this project).
        expire_seconds (int): expire time in seconds.
        refresh (bool | None, optional): if set True, token is refresh token.

    Returns:
        tuple[str, datetime, datetime]: token str, expires_at, issued_at.
    """
    issued_at = int(time.time())
    expires_at = issued_at + expire_seconds
    to_encode: dict[str, int | str | bool] = {
        "issued_at": issued_at,
        "expires_at": expires_at,
        "sub": str(subject),
        "refresh": refresh,
    }
    encode_jwt = jwt.encode(to_encode, key=settings.SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encode_jwt, expires_at, issued_at


def generate_access_token_response(subject: int) -> AccessToken:
    """Generate tokens and return AccessTokenResponse."""
    at, et, it = create_jwt_token(subject, ACCESS_TOKEN_EXPIRE_SECS, refresh=False)
    rat, ret, rit = create_jwt_token(subject, REFRESH_TOKEN_EXPIRE_SECS, refresh=True)
    return AccessToken(
        access_token=at,
        expires_at=et,
        issued_at=it,
        refresh_token=rat,
        refresh_token_expires_at=ret,
        refresh_token_issued_at=rit,
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain and hashed password matches."""
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Create hashed password from plain password."""
    return PWD_CONTEXT.hash(password)
