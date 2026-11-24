import asyncio
import logging
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession

from app.audio_censor import AudioCensor
from app.database.models import Audio
from app.service.exceptions import AudioProcessingError, InvalidUploadError
from app.utils import get_upload_path, save_file

logger = logging.getLogger(__name__)

# Loads both models once, when this module is first imported.
# AudioService is built per request, so it reuses this instance instead of
# reloading the Whisper models every time.
_audio_censor = AudioCensor()
# Only one request uses the shared models at a time.
_audio_censor_lock = asyncio.Lock()


class AudioService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.ac = _audio_censor

    async def get_audio_by_id(self, audio_id: UUID) -> Audio | None:
        """Return the Audio row with the given ID, or None if not found."""
        return await self.session.get(Audio, audio_id)

    def _censor_file(self, file_path: str, output_path: str) -> None:
        """Blocking CPU work: transcribe, flag profanity, write the beeped file."""
        words = self.ac.transcribe_audio(file_path)
        self.ac.mute_audio(
            input_path=file_path,
            output_path=output_path,
            words=self.ac.profanity_check(words["word_segments"]),
        )

    async def censor_audio(self, audio_file: UploadFile) -> Audio:
        """Save the upload, beep out profanity, record it in the DB and return the row."""
        if not audio_file.filename:
            raise InvalidUploadError("The uploaded file has no filename.")
        filename = Path(audio_file.filename).name
        if not filename:
            raise InvalidUploadError("The uploaded file has no usable filename.")
        censored_filename = f"censored_{filename}"

        # Save the upload first: transcribe_audio reads the file from disk.
        try:
            file_path = await asyncio.to_thread(save_file, audio_file)
        except OSError as exc:
            raise AudioProcessingError(f"Could not save '{filename}'.") from exc

        output_path = get_upload_path(censored_filename)
        try:
            # Run the slow model work in a thread so the event loop stays free.
            async with _audio_censor_lock:
                await asyncio.to_thread(self._censor_file, file_path, output_path)
        except Exception as exc:
            # ffmpeg/whisperx/pydub raise assorted errors (RuntimeError,
            # CouldntDecodeError, KeyError...) for files they cannot read.
            logger.exception("Censoring failed for %s", file_path)
            raise AudioProcessingError(
                f"Could not process '{filename}'. Make sure it is a valid audio file."
            ) from exc

        # Only record the row once the censored file actually exists.
        audio = Audio(filepath=filename, censored_filepath=censored_filename)
        try:
            self.session.add(audio)
            await self.session.commit()
            await self.session.refresh(audio)
        except Exception:
            await self.session.rollback()
            raise
        return audio
