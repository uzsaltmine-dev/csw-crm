"""Arizalar statistikasi: bugun, joriy oy, oxirgi 10 va 5 kun. Manager — o'z tumanlari, admin — barcha tumanlar.

Ko'rsatkichlar davrda ochilgan arizalar bo'yicha (bekor qilinganlar hisobga olinmaydi):
  received  — tushgan;  repeat — shundan qayta arizalar;
  done      — bajarilgan (done + suspect);
  overdue   — bajarilmagan va 72 soatlik muddat o'tgan;  pending — bajarilmagan, muddat ichida kutilmoqda;
  not_done  — overdue + pending;  ulushlar — tushganga nisbatan, %.
"""
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import invalid
from app.db.base import utcnow
from app.models import District, Request, User
from app.models.enums import DONE_STATUSES, OPEN_STATUSES, RequestStatus
from app.schemas import DistrictStats, StatMetrics, StatsOut
from app.services import access

TASHKENT = timezone(timedelta(hours=5))
PERIODS = ("today", "month", "last10", "last5")


def period_start(period: str, now_utc: datetime | None = None) -> datetime:
    """Davr boshi (UTC, tzinfo'siz — bazadagi kabi). "Bugun" va "oy" Toshkent vaqti bo'yicha."""
    now = (now_utc or utcnow()).replace(tzinfo=timezone.utc).astimezone(TASHKENT)
    if period == "today":
        start = datetime.combine(now.date(), time.min, TASHKENT)
    elif period == "month":
        start = datetime.combine(now.date().replace(day=1), time.min, TASHKENT)
    elif period in ("last10", "last5"):
        start = now - timedelta(days=10 if period == "last10" else 5)
    else:
        raise invalid("bad_period", "Davr: today, month, last10, last5")
    return start.astimezone(timezone.utc).replace(tzinfo=None)


def _metrics(rows: list[Request], now: datetime) -> dict:
    m = {"received": len(rows), "repeat": 0, "pending": 0, "overdue": 0, "done": 0}
    for r in rows:
        m["repeat"] += r.is_repeat
        st = r.status.value
        if st in DONE_STATUSES:
            m["done"] += 1
        elif st in OPEN_STATUSES:
            m["overdue" if r.due_at and now > r.due_at else "pending"] += 1
    m["not_done"] = m["pending"] + m["overdue"]
    n = m["received"] or 1
    m["done_share"] = round(100 * m["done"] / n, 1) if m["received"] else 0.0
    m["not_done_share"] = round(100 * m["not_done"] / n, 1) if m["received"] else 0.0
    return m


async def summary(db: AsyncSession, actor: User, period: str) -> StatsOut:
    since = period_start(period)
    s = access.scope(actor)
    q = select(Request).where(Request.created_at >= since, Request.status != RequestStatus.cancelled)
    dq = select(District).order_by(District.region_id, District.id)
    if s is not None:
        q = q.where(Request.district_id.in_(s or {-1}))
        dq = dq.where(District.id.in_(s or {-1}))
    rows = list((await db.execute(q)).scalars())
    now = utcnow()
    by_d: dict[int, list[Request]] = {}
    for r in rows:
        by_d.setdefault(r.district_id, []).append(r)
    districts = [DistrictStats(district_id=d.id, name=d.name, **_metrics(by_d.get(d.id, []), now))
                 for d in (await db.execute(dq)).scalars()]
    return StatsOut(period=period, since=since, total=StatMetrics(**_metrics(rows, now)), districts=districts)
