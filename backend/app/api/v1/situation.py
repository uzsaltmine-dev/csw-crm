"""Vaziyat paneli: faqat admin uchun hodisalar jurnali (90 kun)."""
import json
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_roles
from app.models import SituationEvent, SituationRead, User
from app.models.enums import Role, SituationLevel
from app.schemas import SituationOut, SituationPage, SituationReadIn

router = APIRouter(prefix="/situation", tags=["situation"])
Viewer = Depends(require_roles(Role.admin))


async def _last_read(db: AsyncSession, user_id: int) -> int:
    return (await db.execute(select(SituationRead.last_read_id).where(SituationRead.user_id == user_id))).scalar() or 0


async def _unread(db: AsyncSession, last_read: int) -> int:
    return (await db.execute(select(func.count()).select_from(SituationEvent).where(SituationEvent.id > last_read))).scalar_one()


@router.get("", response_model=SituationPage)
async def events(level: SituationLevel | None = None, kind: str | None = Query(None, max_length=40), district_id: int | None = None,
                 date_from: date | None = None, date_to: date | None = None, unread: bool = False,
                 limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), user: User = Viewer, db: AsyncSession = DB):
    last = await _last_read(db, user.id)
    cond = []
    if level:
        cond.append(SituationEvent.level == level)
    if kind:
        cond.append(SituationEvent.kind == kind)
    if district_id:
        cond.append(SituationEvent.district_id == district_id)
    # Sanalar Toshkent vaqti bo'yicha (UTC+5), bazada UTC saqlanadi
    if date_from:
        cond.append(SituationEvent.created_at >= datetime.combine(date_from, time.min) - timedelta(hours=5))
    if date_to:
        cond.append(SituationEvent.created_at < datetime.combine(date_to + timedelta(days=1), time.min) - timedelta(hours=5))
    if unread:
        cond.append(SituationEvent.id > last)
    total = (await db.execute(select(func.count()).select_from(SituationEvent).where(*cond))).scalar_one()
    rows = (await db.execute(select(SituationEvent, User.full_name).outerjoin(User, User.id == SituationEvent.actor_id)
                             .where(*cond).order_by(SituationEvent.id.desc()).limit(limit).offset(offset))).all()
    pending_refs = [e.ref_id for e, _ in rows if e.kind == "staff_pending" and e.ref_id]
    still_pending = set((await db.execute(select(User.id).where(User.id.in_(pending_refs), User.approval_status == "pending"))).scalars()) \
        if pending_refs else set()
    items = [SituationOut(id=e.id, level=e.level.value, kind=e.kind, message=e.message, params=json.loads(e.params) if e.params else {},
                          district_id=e.district_id, actor_id=e.actor_id, actor_name=name, ref_type=e.ref_type, ref_id=e.ref_id,
                          created_at=e.created_at, resolved=e.kind == "staff_pending" and e.ref_id not in still_pending)
             for e, name in rows]
    return SituationPage(items=items, total=total, unread=await _unread(db, last), last_read_id=last)


@router.get("/unread")
async def unread_count(user: User = Viewer, db: AsyncSession = DB) -> dict:
    return {"unread": await _unread(db, await _last_read(db, user.id))}


@router.post("/read")
async def mark_read(body: SituationReadIn, user: User = Viewer, db: AsyncSession = DB) -> dict:
    newest = (await db.execute(select(func.max(SituationEvent.id)))).scalar() or 0
    up_to = min(body.up_to_id, newest) if body.up_to_id is not None else newest
    row = await db.get(SituationRead, user.id)
    if row is None:
        db.add(SituationRead(user_id=user.id, last_read_id=up_to))
    elif up_to > row.last_read_id:  # orqaga qaytmaydi
        row.last_read_id = up_to
    await db.commit()
    last = await _last_read(db, user.id)
    return {"unread": await _unread(db, last), "last_read_id": last}
