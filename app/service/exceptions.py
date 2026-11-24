class AudioServiceError(Exception):
    """Base class for errors the audio service raises on purpose."""


class InvalidUploadError(AudioServiceError):
    """The upload is missing a filename or is otherwise unusable (client error)."""


class AudioProcessingError(AudioServiceError):
    """The file could not be decoded, transcribed or censored."""
