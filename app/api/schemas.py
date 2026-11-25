from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AudioRead(BaseModel):
    id: UUID
    created_at: datetime
    filepath: str
    censored_filepath: str


class UserCreate(BaseModel):
    # Letters, digits, "_", "." and "-" only.
    username: str = Field(min_length=3, max_length=50, pattern=r"^[A-Za-z0-9_.-]+$")
    email: EmailStr
    # Plain password from the client; the server hashes it before saving.
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    # Never include the password hash in responses.
    id: UUID
    created_at: datetime
    username: str
    email: EmailStr


class Token(BaseModel):
    # Standard OAuth2 token response.
    access_token: str
    token_type: str = "bearer"
