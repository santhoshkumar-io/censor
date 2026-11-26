import asyncio
import logging
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.database.models import Audio, AudioStatus
from app.service.exceptions import (
    AudioProcessingError,
    InvalidUploadError,
    TaskQueueError,
)
from app.utils import save_file
from app.worker.tasks import censor_audio_task

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_audio_by_id(self, audio_id: UUID) -> Audio | None:
        """Return the Audio row with the given ID, or None if not found."""
        return await self.session.get(Audio, audio_id)

    async def list_audio(self, limit: int = 50, offset: int = 0) -> list[Audio]:
        """Return Audio rows, newest first."""
        result = await self.session.exec(
            select(Audio).order_by(desc(Audio.created_at)).offset(offset).limit(limit)
        )
        return list(result.all())

    async def censor_audio(self, audio_file: UploadFile, user_id: UUID) -> Audio:
        """Save the upload, record it as pending and queue the censoring task.

        The Celery worker does the slow model work and updates ``status``
        (processing -> completed / failed) and ``censored_filepath``.
        """
        if not audio_file.filename:
            raise InvalidUploadError("The uploaded file has no filename.")
        filename = Path(audio_file.filename).name
        if not filename:
            raise InvalidUploadError("The uploaded file has no usable filename.")

        # Save the upload first: the worker reads the file from disk.
        try:
            await asyncio.to_thread(save_file, audio_file)
        except OSError as exc:
            raise AudioProcessingError(f"Could not save '{filename}'.") from exc

        audio = Audio(filepath=filename, user_id=user_id, status=AudioStatus.pending)
        try:
            self.session.add(audio)
            await self.session.commit()
            await self.session.refresh(audio)
        except Exception:
            await self.session.rollback()
            raise

        # Queue only after the commit, so the worker can find the row.
        try:
            # .delay() talks to the broker over the network; keep it off the event loop.
            await asyncio.to_thread(censor_audio_task.delay, str(audio.id))
        except Exception as exc:
            logger.exception("Could not queue censoring for audio %s", audio.id)
            audio.status = AudioStatus.failed
            self.session.add(audio)
            await self.session.commit()
            raise TaskQueueError(
                "The audio was saved but could not be queued for processing."
            ) from exc
        return audio
