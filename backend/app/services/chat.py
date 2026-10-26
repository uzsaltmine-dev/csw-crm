"""Ariza va murojaat ichidagi yozishma.

Kim ko'radi: admin — hammasi; manager, yurist, operator — o'z tumanlari; GPS — o'z tumanidagi arizalar;
haydovchi — faqat o'ziga biriktirilgan ariza. Murojaat yozishmasini GPS va haydovchi ko'rmaydi.
Ariza/murojaat yopilgach yozishma faqat o'qish uchun (manager va admin yoza oladi).
Murojaat qabul qilinib ariza ochilsa, murojaat yozishmasi ariza yozishmasining boshida ko'rinadi.
Ovozli xabar: 60 soniyagacha, audio 90 kun saqlanadi.
"""
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import realtime
from app.core.errors import forbidden, invalid, not_found
from app.db.base import utcnow
from app.models import Appeal, ChatMessage, ChatRead, Customer, Request, User
from app.models.enums import AppealStatus, RequestStatus, Role
from app.services import access
from app.services.storage import Storage

THREADS = ("request", "appeal")
MAX_TEXT = 2000
MAX_VOICE_S = 60
MAX_VOICE_BYTES = 2 * 1024 * 1024
VOICE_TYPES = {"audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "m4a", "audio/mpeg": "mp3", "audio/aac": "aac"}
RETENTION_DAYS = 90
CLOSED_REQUEST = {RequestStatus.done, RequestStatus.suspect, RequestStatus.cancelled}
WRITE_WHEN_CLOSED = {Role.admin, Role.manager}


@dataclass
class Thread:
    type: str
    id: int
    district_id: int
    closed: bool
    driver_id: int | None
    number: str | None
    title: str
    request_id: int | None  # murojaat ariza bo'lib ochilgan bo'lsa — o'sha ariza
    appeal_id: int | None   # ariza murojaatdan ochilgan bo'lsa — o'sha murojaat


async def load_thread(db: AsyncSession, thread_type: str, thread_id: int) -> Thread:
    if thread_type == "request":
        r = await db.get(Request, thread_id)
        if not r:
            raise not_found("request")
        cust = await db.get(Customer, r.customer_id)
        appeal_id = (await db.execute(select(Appeal.id).where(Appeal.request_id == r.id))).scalar_one_or_none()
        return Thread("request", r.id, r.district_id, r.status in CLOSED_REQUEST, r.driver_id, r.number,
                      cust.name if cust else "", r.id, appeal_id)
    if thread_type == "appeal":
        a = await db.get(Appeal, thread_id)
        if not a:
            raise not_found("appeal")
        return Thread("appeal", a.id, a.district_id, a.status != AppealStatus.new, None, a.number, a.org_name,
                      a.request_id, a.id)
    raise invalid("bad_thread", "Yozishma turi: request yoki appeal")


def can_view(user: User, t: Thread) -> bool:
    if not user.is_active or not user.can("chat.view"):
        return False
    if user.role == Role.admin:
        return True
    if user.role == Role.driver:
        return t.type == "request" and t.driver_id == user.id
    if user.role == Role.gps and t.type == "appeal":
        return False
    return access.in_scope(user, t.district_id)


def can_write(user: User, t: Thread) -> bool:
    return can_view(user, t) and user.can("chat.write") and (not t.closed or user.role in WRITE_WHEN_CLOSED)


def check_view(user: User, t: Thread) -> None:
    if not can_view(user, t):
        raise forbidden("Bu yozishmani ko'rish uchun ruxsat yo'q")


def _threads_cond(t: Thread):
    """Ariza yozishmasi = ariza xabarlari + (bo'lsa) murojaat xabarlari."""
    conds = [and_(ChatMessage.thread_type == t.type, ChatMessage.thread_id == t.id)]
    if t.type == "request" and t.appeal_id:
        conds.append(and_(ChatMessage.thread_type == "appeal", ChatMessage.thread_id == t.appeal_id))
    return or_(*conds)


def out(m: ChatMessage) -> dict:
    return {"id": m.id, "thread_type": m.thread_type, "thread_id": m.thread_id, "author_id": m.author_id,
            "author_name": m.author.full_name if m.author else "", "author_role": m.author.role.value if m.author else None,
            "kind": m.kind, "text": m.text, "duration_s": m.duration_s, "expired": m.expired,
            "has_audio": m.kind == "voice" and bool(m.file_key) and not m.expired, "created_at": m.created_at}


async def messages(db: AsyncSession, user: User, thread_type: str, thread_id: int, before_id: int | None,
                   limit: int) -> dict:
    t = await load_thread(db, thread_type, thread_id)
    check_view(user, t)
    q = select(ChatMessage).where(_threads_cond(t))
    if before_id:
        q = q.where(ChatMessage.id < before_id)
    rows = list((await db.execute(q.order_by(ChatMessage.id.desc()).limit(limit + 1))).scalars())
    more = len(rows) > limit
    rows = list(reversed(rows[:limit]))
    return {"thread_type": t.type, "thread_id": t.id, "number": t.number, "title": t.title, "closed": t.closed,
            "can_write": can_write(user, t), "appeal_id": t.appeal_id if t.type == "request" else None,
            "has_more": more, "items": [out(m) for m in rows]}


async def _recipients(db: AsyncSession, t: Thread) -> list[int]:
    users = (await db.execute(select(User).where(User.is_active.is_(True), User.approval_status == "approved"))).scalars()
    return [u.id for u in users if can_view(u, t)]


async def _post(db: AsyncSession, user: User, t: Thread, m: ChatMessage) -> dict:
    db.add(m)
    await db.flush()
    await _mark_read(db, user.id, t, m.id)
    await db.commit()
    await db.refresh(m, ["author"])
    payload = out(m) | {"thread": {"type": t.type, "id": t.id, "number": t.number, "title": t.title,
                                   "district_id": t.district_id, "request_id": t.request_id}}
    await realtime.emit_chat_message(payload, await _recipients(db, t))
    return out(m)


async def _writable(db: AsyncSession, user: User, thread_type: str, thread_id: int) -> Thread:
    t = await load_thread(db, thread_type, thread_id)
    check_view(user, t)
    if not can_write(user, t):
        if t.closed:
            raise forbidden("Yozishma yopilgan: ariza yoki murojaat yakunlangan")
        raise forbidden("Bu yozishmaga yozish uchun ruxsat yo'q")
    return t


async def post_text(db: AsyncSession, user: User, thread_type: str, thread_id: int, text: str) -> dict:
    text = (text or "").strip()
    if not text:
        raise invalid("empty_message", "Xabar bo'sh")
    if len(text) > MAX_TEXT:
        raise invalid("message_too_long", f"Xabar {MAX_TEXT} belgidan oshmasin")
    t = await _writable(db, user, thread_type, thread_id)
    return await _post(db, user, t, ChatMessage(thread_type=t.type, thread_id=t.id, author_id=user.id, kind="text", text=text))


async def post_voice(db: AsyncSession, storage: Storage, user: User, thread_type: str, thread_id: int, data: bytes,
                     content_type: str, duration_s: float) -> dict:
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype not in VOICE_TYPES:
        raise invalid("bad_audio", "Ovoz formati qo'llab-quvvatlanmaydi (webm, ogg, m4a, mp3)")
    if not data:
        raise invalid("bad_audio", "Ovozli xabar bo'sh")
    if len(data) > MAX_VOICE_BYTES:
        raise invalid("voice_too_large", "Ovozli xabar 2 MB dan oshmasin")
    if duration_s <= 0 or duration_s > MAX_VOICE_S + 1:
        raise invalid("voice_too_long", f"Ovozli xabar {MAX_VOICE_S} soniyadan oshmasin")
    t = await _writable(db, user, thread_type, thread_id)
    key = f"chat/{t.type}/{t.id}/{uuid4().hex}.{VOICE_TYPES[ctype]}"
    storage.put(key, data, ctype)
    m = ChatMessage(thread_type=t.type, thread_id=t.id, author_id=user.id, kind="voice", file_key=key, content_type=ctype,
                    duration_s=max(1, round(duration_s)))
    return await _post(db, user, t, m)


async def audio(db: AsyncSession, storage: Storage, user: User, message_id: int) -> tuple[bytes, str]:
    m = await db.get(ChatMessage, message_id)
    if not m or m.kind != "voice":
        raise not_found("message")
    t = await load_thread(db, m.thread_type, m.thread_id)
    if not can_view(user, t):
        # murojaat xabari ariza yozishmasi orqali ham ko'rinadi
        linked = t.type == "appeal" and t.request_id and can_view(user, await load_thread(db, "request", t.request_id))
        if not linked:
            raise forbidden("Bu yozishmani ko'rish uchun ruxsat yo'q")
    if m.expired or not m.file_key:
        raise not_found("audio")
    return storage.get(m.file_key), m.content_type or "audio/webm"


async def _mark_read(db: AsyncSession, user_id: int, t: Thread, upto: int | None = None) -> None:
    keys = [(t.type, t.id)] + ([("appeal", t.appeal_id)] if t.type == "request" and t.appeal_id else [])
    for tt, tid in keys:
        last = upto or (await db.execute(select(func.max(ChatMessage.id)).where(
            ChatMessage.thread_type == tt, ChatMessage.thread_id == tid))).scalar_one() or 0
        row = await db.get(ChatRead, (user_id, tt, tid))
        if row is None:
            db.add(ChatRead(user_id=user_id, thread_type=tt, thread_id=tid, last_read_id=last))
        elif last > row.last_read_id:
            row.last_read_id = last


async def mark_read(db: AsyncSession, user: User, thread_type: str, thread_id: int) -> None:
    t = await load_thread(db, thread_type, thread_id)
    check_view(user, t)
    await _mark_read(db, user.id, t)
    await db.commit()


async def unread(db: AsyncSession, user: User) -> dict:
    """O'qilmagan xabarlar: o'zi yozmagan, oxirgi 90 kundagi, ko'rish mumkin bo'lgan yozishmalarda.
    Ariza ochilgan murojaatning xabarlari ariza hisobiga qo'shiladi."""
    if not user.can("chat.view"):
        return {"total": 0, "threads": []}
    since = utcnow() - timedelta(days=RETENTION_DAYS)
    r = ChatRead
    q = (select(ChatMessage.thread_type, ChatMessage.thread_id, func.count(), func.max(ChatMessage.id))
         .outerjoin(r, and_(r.user_id == user.id, r.thread_type == ChatMessage.thread_type, r.thread_id == ChatMessage.thread_id))
         .where(ChatMessage.author_id != user.id, ChatMessage.created_at >= since,
                ChatMessage.id > func.coalesce(r.last_read_id, 0))
         .group_by(ChatMessage.thread_type, ChatMessage.thread_id))
    acc: dict[tuple[str, int], dict] = {}
    for tt, tid, n, last in (await db.execute(q)).all():
        t = await load_thread(db, tt, tid)
        if t.type == "appeal" and t.request_id:  # murojaat ariza bo'lib ochilgan — ariza yozishmasida ko'rinadi
            t = await load_thread(db, "request", t.request_id)
        if not can_view(user, t):
            continue
        cur = acc.setdefault((t.type, t.id), {"thread_type": t.type, "thread_id": t.id, "number": t.number, "title": t.title,
                                              "district_id": t.district_id, "count": 0, "last_id": 0})
        cur["count"] += n
        cur["last_id"] = max(cur["last_id"], last)
    threads = sorted(acc.values(), key=lambda x: -x["last_id"])
    return {"total": sum(x["count"] for x in threads), "threads": threads}


async def purge_voice(db: AsyncSession, storage: Storage) -> int:
    """90 kundan eski ovozli xabarlarning audiosini o'chiradi (xabar o'zi "muddati tugagan" bo'lib qoladi)."""
    old = list((await db.execute(select(ChatMessage).where(
        ChatMessage.kind == "voice", ChatMessage.expired.is_(False),
        ChatMessage.created_at < utcnow() - timedelta(days=RETENTION_DAYS)))).scalars())
    for m in old:
        if m.file_key:
            try:
                storage.delete(m.file_key)
            except Exception:  # noqa: BLE001 — fayl allaqachon yo'q bo'lsa ham belgilaymiz
                pass
        m.expired, m.file_key = True, None
    await db.commit()
    return len(old)
