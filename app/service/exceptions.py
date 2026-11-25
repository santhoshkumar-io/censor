class AudioServiceError(Exception):
    """Base class for errors the audio service raises on purpose."""


class InvalidUploadError(AudioServiceError):
    """The upload is missing a filename or is otherwise unusable (client error)."""


class AudioProcessingError(AudioServiceError):
    """The file could not be decoded, transcribed or censored."""


class UserAlreadyExistsError(Exception):
    """A user with this email is already registered."""


class InvalidCredentialsError(Exception):
    """The username/email and password do not match a user."""


class InvalidTokenError(Exception):
    """The access token is malformed, expired, badly signed or points to no user."""
