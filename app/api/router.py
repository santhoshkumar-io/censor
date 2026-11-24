from uuid import UUID

from fastapi import APIRouter, HTTPException, UploadFile, status

from app.api.dependcies import AudioServiceDep
from app.api.schemas import AudioRead
from app.service.exceptions import AudioProcessingError, InvalidUploadError

router = APIRouter()


@router.post("/audio", response_model=AudioRead, status_code=status.HTTP_201_CREATED)
async def submit_audio(audio_file: UploadFile, service: AudioServiceDep):
    try:
        return await service.censor_audio(audio_file)
    except InvalidUploadError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AudioProcessingError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("/audio/{audio_id}", response_model=AudioRead)
async def read_audio(audio_id: UUID, service: AudioServiceDep):
    audio = await service.get_audio_by_id(audio_id)
    if not audio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Audio not found")
    return audio
