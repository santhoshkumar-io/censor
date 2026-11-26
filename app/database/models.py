from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "user"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    username: str
    email: str
    password_hash: str

    # One user has many uploads. "user" is the matching attribute on Audio.
    audios: list["Audio"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class AudioStatus(str, Enum):
    pending="pending"
    processing="processing"
    completed="completed"
    failed="failed"
    
class Audio(SQLModel, table=True):
    __tablename__ = "audio"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    filepath: str
    censored_filepath: str| None = Field(default=None)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    status: AudioStatus= Field(default=AudioStatus.pending)
    # Each upload belongs to one user. "audios" is the matching attribute on User.
    user: User = Relationship(back_populates="audios" ,sa_relationship_kwargs={"lazy": "selectin"},)
