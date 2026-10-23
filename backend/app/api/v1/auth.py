from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, current_user
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import ACCESS, REFRESH, create_token, decode_token
from app.models import User
from app.repositories import users as users_repo
from app.schemas import LoginIn, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])
REFRESH_PATH = "/api/v1/auth"


def _set_cookies(resp: Response, user: User) -> None:
    s = get_settings()
    common = {"httponly": True, "secure": s.cookie_secure, "samesite": "lax"}
    resp.set_cookie("access_token", create_token(user.id, user.role.value, ACCESS),
                    max_age=s.access_token_minutes * 60, path="/", **common)
    resp.set_cookie("refresh_token", create_token(user.id, user.role.value, REFRESH),
                    max_age=s.refresh_token_days * 86400, path=REFRESH_PATH, **common)


@router.post("/login", response_model=UserOut)
async def login(body: LoginIn, response: Response, db: AsyncSession = DB):
    user = await auth_service.login(db, body.username, body.password)
    _set_cookies(response, user)
    return user


@router.post("/refresh", response_model=UserOut)
async def refresh(request: Request, response: Response, db: AsyncSession = DB):
    token = request.cookies.get("refresh_token")
    data = decode_token(token, REFRESH) if token else None
    user = await users_repo.by_id(db, int(data["sub"])) if data else None
    if not user or not user.is_active:
        raise AppError(401, "not_authenticated", "Sessiya tugadi, qayta kiring")
    _set_cookies(response, user)
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path=REFRESH_PATH)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return user
