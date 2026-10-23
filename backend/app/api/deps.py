from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, forbidden
from app.core.security import ACCESS, decode_token
from app.db.session import get_session
from app.models import User
from app.models.enums import Role
from app.repositories import users as users_repo
from app.services.storage import Storage

DB = Depends(get_session)


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


def _token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:]
    return request.cookies.get("access_token")


async def current_user(request: Request, db: AsyncSession = DB) -> User:
    token = _token(request)
    data = decode_token(token, ACCESS) if token else None
    if not data:
        raise AppError(401, "not_authenticated", "Tizimga kiring")
    user = await users_repo.by_id(db, int(data["sub"]))
    if not user or not user.is_active:
        raise AppError(401, "not_authenticated", "Tizimga kiring")
    return user


def require_roles(*roles: Role) -> Callable:
    async def checker(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise forbidden()
        return user
    return checker
