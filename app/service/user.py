import asyncio
from uuid import UUID

from pwdlib import PasswordHash
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from app.api.schemas import UserCreate
from app.database.models import User
from app.security import create_access_token
from app.service.exceptions import InvalidCredentialsError, UserAlreadyExistsError

# Argon2id with pwdlib's recommended settings.
password_hasher = PasswordHash.recommended()
# Checked when the user does not exist, so a wrong username takes as long as a
# wrong password and response times do not reveal which usernames exist.
_DUMMY_HASH = password_hasher.hash("dummy-password-for-timing")


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_user_by_email(self, email: str) -> User | None:
        result = await self.session.exec(select(User).where(User.email == email))
        return result.first()

    async def get_user_by_username(self, username: str) -> User | None:
        result = await self.session.exec(select(User).where(User.username == username))
        return result.first()

    async def add_user(self, user_create: UserCreate) -> User:
        """Hash the password and save a new user. Raises if the username or email is taken."""
        # Usernames and emails are compared case-insensitively.
        username = user_create.username.lower()
        email = user_create.email.lower()
        if await self.get_user_by_username(username):
            raise UserAlreadyExistsError(f"The username '{username}' is already taken.")
        if await self.get_user_by_email(email):
            raise UserAlreadyExistsError(f"A user with email '{email}' already exists.")

        # Argon2 is deliberately slow; hash in a thread so the event loop stays free.
        password_hash = await asyncio.to_thread(
            password_hasher.hash, user_create.password
        )

        user = User(username=username, email=email, password_hash=password_hash)
        self.session.add(user)
        try:
            await self.session.commit()
        except IntegrityError as exc:
            # Two requests registered the same username or email at the same moment.
            await self.session.rollback()
            raise UserAlreadyExistsError(
                "That username or email is already registered."
            ) from exc
        await self.session.refresh(user)
        return user

    async def authenticate_user(self, login: str, password: str) -> User:
        """Return the user if ``login`` (username or email) and password match.

        Raises InvalidCredentialsError otherwise, without saying which part was wrong.
        """
        login = login.strip().lower()
        if "@" in login:
            user = await self.get_user_by_email(login)
        else:
            user = await self.get_user_by_username(login)

        stored_hash = user.password_hash if user else _DUMMY_HASH
        # Argon2 is deliberately slow; verify in a thread so the event loop stays free.
        password_ok = await asyncio.to_thread(
            password_hasher.verify, password, stored_hash
        )
        if not user or not password_ok:
            raise InvalidCredentialsError("Incorrect username or password.")
        return user

    async def login(self, login: str, password: str) -> str:
        """Check the credentials and return a JWT access token for the user."""
        user = await self.authenticate_user(login, password)
        return create_access_token(user.id)
