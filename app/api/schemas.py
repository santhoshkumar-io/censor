from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AudioRead(BaseModel):
    id: UUID
    created_at: datetime
    filepath: str
    censored_filepath: str
