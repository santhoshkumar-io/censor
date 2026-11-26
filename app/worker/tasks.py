import logging
from uuid import UUID

from celery import Celery, Task
from sqlalchemy.engine import make_url
from sqlmodel import Session, create_engine

from app.config import settings
from app.database.models import Audio, AudioStatus
from app.utils import get_upload_path

logger = logging.getLogger(__name__)

celery_app = Celery("tasks", broker=settings.BROKER_URL)


def _sync_db_url(url: str) -> str:
    """Celery tasks are synchronous, so use psycopg instead of asyncpg."""
    parsed = make_url(url)
    if parsed.drivername.startswith("postgresql"):
        parsed = parsed.set(drivername="postgresql+psycopg")
    return parsed.render_as_string(hide_password=False)


class CensorTask(Task):
    """Base task that loads the models and DB engine once per worker process.

    Celery creates task objects when this module is imported, and the API imports
    it to call ``.delay()``. Loading lazily keeps WhisperX out of the API process.
    """

    _ac = None
    _engine = None

    @property
    def ac(self):
        if self._ac is None:
            # Imported here so the API never imports whisperx.
            from app.worker.audio_censor import AudioCensor

            self._ac = AudioCensor()
        return self._ac

    def session_local(self) -> Session:
        if self._engine is None:
            self._engine = create_engine(_sync_db_url(settings.DB_URL))
        return Session(self._engine)


@celery_app.task(base=CensorTask, bind=True)
def censor_audio_task(self: CensorTask, audio_id: str) -> None:
    """Beep out profanity in the uploaded file and record the result on the row."""
    with self.session_local() as session:
        audio = session.get(Audio, UUID(audio_id))
        if audio is None:
            logger.warning("Audio %s not found; nothing to censor", audio_id)
            return

        audio.status = AudioStatus.processing
        session.add(audio)
        session.commit()

        # The row stores bare filenames; the files live in the uploads folder.
        input_path = get_upload_path(audio.filepath)
        censored_filename = f"censored_{audio.filepath}"
        output_path = get_upload_path(censored_filename)

        try:
            words = self.ac.transcribe_audio(input_path)
            self.ac.mute_audio(
                input_path=input_path,
                output_path=output_path,
                words=self.ac.profanity_check(words["word_segments"]),
            )
        except Exception:
            # ffmpeg/whisperx/pydub raise assorted errors for unreadable files.
            logger.exception("Censoring failed for audio %s (%s)", audio_id, input_path)
            audio.status = AudioStatus.failed
        else:
            audio.censored_filepath = censored_filename
            audio.status = AudioStatus.completed

        session.add(audio)
        session.commit()
