from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import verify_password
from app.db.base import utcnow
from app.models import User
from app.repositories import users as users_repo


async def login(db: AsyncSession, username: str, password: str) -> User:
    s = get_settings()
    user = await users_repo.by_username(db, username.strip().lower())
    bad = AppError(401, "invalid_credentials", "Login yoki parol noto'g'ri")
    if not user or not user.is_active:
        raise bad
    now = utcnow()
    if user.locked_until and user.locked_until > now:
        raise AppError(423, "account_locked", f"Juda ko'p xato urinish. {s.login_lock_minutes} daqiqadan keyin qayta urinib ko'ring")
    if not verify_password(password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= s.login_max_attempts:
            user.locked_until = now + timedelta(minutes=s.login_lock_minutes)
            user.failed_logins = 0
        await db.commit()
        raise bad
    user.failed_logins = 0
    user.locked_until = None
    await db.commit()
    return user
