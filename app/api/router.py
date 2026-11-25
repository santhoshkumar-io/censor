from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.dependcies import (
    AudioServiceDep,
    CurrentUserDep,
    UserServiceDep,
    get_current_user,
)
from app.api.schemas import AudioRead, Token, UserCreate, UserRead
from app.service.exceptions import (
    AudioProcessingError,
    InvalidCredentialsError,
    InvalidUploadError,
    UserAlreadyExistsError,
)

# Public: signing up and logging in must work without a token.
auth_router = APIRouter(tags=["auth"])
# Protected: every route on this router needs a valid bearer token (401 otherwise).
audio_router = APIRouter(tags=["audio"], dependencies=[Depends(get_current_user)])


@auth_router.post("/signup", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate, service: UserServiceDep):
    try:
        return await service.add_user(user)
    except UserAlreadyExistsError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@auth_router.post("/token", response_model=Token)
async def login_user(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    service: UserServiceDep,
):
    """OAuth2 password flow: form fields ``username`` (username or email) and ``password``."""
    try:
        access_token = await service.login(form_data.username, form_data.password)
    except InvalidCredentialsError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return Token(access_token=access_token, token_type="bearer")


@audio_router.post("/audio", response_model=AudioRead, status_code=status.HTTP_201_CREATED)
async def submit_audio(
    audio_file: UploadFile, service: AudioServiceDep, user: CurrentUserDep
):
    # FastAPI caches get_current_user per request, so this reuses the
    # router-level check rather than decoding the token twice.
    try:
        return await service.censor_audio(audio_file, user_id=user.id)
    except InvalidUploadError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AudioProcessingError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@audio_router.get("/audio", response_model=list[AudioRead])
async def list_audio(
    service: AudioServiceDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
):
    """List uploaded audio, newest first, so you can find an ``id``."""
    return await service.list_audio(limit=limit, offset=offset)


@audio_router.get("/audio/{audio_id}", response_model=AudioRead)
async def read_audio(audio_id: UUID, service: AudioServiceDep):
    audio = await service.get_audio_by_id(audio_id)
    if not audio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")
    return audio


# Single router for main.py to include.
router = APIRouter()
router.include_router(auth_router)
router.include_router(audio_router)
