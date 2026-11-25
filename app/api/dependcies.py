from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.models import User
from app.database.session import get_session
from app.security import decode_access_token
from app.service.audio import AudioService
from app.service.exceptions import InvalidTokenError
from app.service.user import UserService

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Reads "Authorization: Bearer <token>"; tokenUrl powers the docs' Authorize button.
oauth2_schema = OAuth2PasswordBearer(tokenUrl="/token")


def get_audio_service(session: SessionDep) -> AudioService:
    return AudioService(session)


def get_user_service(session: SessionDep) -> UserService:
    return UserService(session)


AudioServiceDep = Annotated[AudioService, Depends(get_audio_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]


async def get_current_user(
    token: Annotated[str, Depends(oauth2_schema)],
    service: UserServiceDep,
) -> User:
    """Return the user the bearer token belongs to, or raise 401."""
    credentials_error = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_id = decode_access_token(token)
    except InvalidTokenError as exc:
        raise credentials_error from exc

    # A valid token can still point to a user that has since been deleted.
    user = await service.get_user_by_id(user_id)
    if user is None:
        raise credentials_error
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]
