from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt

from app.config import settings
from app.service.exceptions import InvalidTokenError


def create_access_token(user_id: UUID) -> str:
    """Return a signed JWT whose ``sub`` claim is the user's ID."""
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> UUID:
    """Verify the token's signature and expiry and return the user ID in ``sub``.

    Raises InvalidTokenError if the token cannot be trusted.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            # Only accept the configured algorithm, never one named by the token.
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "exp"]},
        )
        return UUID(payload["sub"])
    except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
        # jwt.InvalidTokenError covers bad signature, expiry and missing claims;
        # ValueError/TypeError cover a "sub" that is not a valid UUID string.
        raise InvalidTokenError("Could not validate credentials.") from exc
