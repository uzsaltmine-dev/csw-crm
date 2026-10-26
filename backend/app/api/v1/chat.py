"""Ariza va murojaat ichidagi yozishma: matn va ovozli xabarlar."""
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, get_storage, require_perm
from app.models import User
from app.services import chat as svc
from app.services.storage import Storage

router = APIRouter(prefix="/chat", tags=["chat"])
View = Depends(require_perm("chat.view"))
Write = Depends(require_perm("chat.write"))
ThreadType = Literal["request", "appeal"]


class TextIn(BaseModel):
    text: str = Field(min_length=1, max_length=svc.MAX_TEXT)


@router.get("/unread")
async def unread(user: User = View, db: AsyncSession = DB) -> dict:
    return await svc.unread(db, user)


@router.get("/audio/{message_id}")
async def audio(message_id: int, user: User = View, db: AsyncSession = DB, storage: Storage = Depends(get_storage)) -> Response:
    data, ctype = await svc.audio(db, storage, user, message_id)
    return Response(data, media_type=ctype, headers={"Cache-Control": "private, max-age=3600"})


@router.get("/{thread_type}/{thread_id}")
async def messages(thread_type: ThreadType, thread_id: int, before_id: int | None = None, limit: int = Query(50, ge=1, le=200),
                   user: User = View, db: AsyncSession = DB) -> dict:
    return await svc.messages(db, user, thread_type, thread_id, before_id, limit)


@router.post("/{thread_type}/{thread_id}/text", status_code=201)
async def post_text(thread_type: ThreadType, thread_id: int, body: TextIn, user: User = Write, db: AsyncSession = DB) -> dict:
    return await svc.post_text(db, user, thread_type, thread_id, body.text)


@router.post("/{thread_type}/{thread_id}/voice", status_code=201)
async def post_voice(thread_type: ThreadType, thread_id: int, duration: float = Form(gt=0), audio: UploadFile = File(...),
                     user: User = Write, db: AsyncSession = DB, storage: Storage = Depends(get_storage)) -> dict:
    data = await audio.read(svc.MAX_VOICE_BYTES + 1)
    return await svc.post_voice(db, storage, user, thread_type, thread_id, data, audio.content_type or "", duration)


@router.post("/{thread_type}/{thread_id}/read", status_code=204)
async def read(thread_type: ThreadType, thread_id: int, user: User = View, db: AsyncSession = DB):
    await svc.mark_read(db, user, thread_type, thread_id)
