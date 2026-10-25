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


# --- tanlangan ko'rsatkich bo'yicha batafsil: dinamika, tarkib, vaqt taqsimoti, tumanlar ---
METRICS = ("received", "repeat", "pending", "overdue", "done", "not_done")
HIST_BUCKETS = (("0-24", 0, 24), ("24-48", 24, 48), ("48-72", 48, 72), ("72+", 72, None))


def _kind(r: Request, now: datetime) -> str:
    st = r.status.value
    if st in DONE_STATUSES:
        return "done"
    return "overdue" if r.due_at and now > r.due_at else "pending"


def _subset(rows: list[Request], metric: str, now: datetime) -> list[Request]:
    if metric == "received":
        return rows
    if metric == "repeat":
        return [r for r in rows if r.is_repeat]
    if metric == "not_done":
        return [r for r in rows if _kind(r, now) != "done"]
    return [r for r in rows if _kind(r, now) == metric]


def _composition(sub: list[Request], metric: str, now: datetime) -> list[dict]:
    """Ko'rsatkich tarkibi (doira diagramma)."""
    if metric == "done":
        keys = ("on_time", "late", "suspect")

        def k(r):
            if r.status.value == "suspect":
                return "suspect"
            return "late" if r.due_at and r.finished_at and r.finished_at > r.due_at else "on_time"
    elif metric in ("pending", "overdue", "not_done"):
        keys = ("unassigned", "in_progress", "failed")

        def k(r):
            st = r.status.value
            return "unassigned" if st == "new" else "failed" if st == "failed" else "in_progress"
    else:
        keys = ("done", "pending", "overdue")

        def k(r):
            return _kind(r, now)
    counts = {x: 0 for x in keys}
    for r in sub:
        counts[k(r)] += 1
    return [{"key": x, "value": v} for x, v in counts.items()]


def _histogram(sub: list[Request], now: datetime) -> list[dict]:
    """Ariza ochilgandan bajarilguncha (bajarilmaganlar uchun — hozirgacha) o'tgan soatlar taqsimoti."""
    counts = {b[0]: 0 for b in HIST_BUCKETS}
    for r in sub:
        end = r.finished_at if r.status.value in DONE_STATUSES and r.finished_at else now
        h = (end - r.created_at).total_seconds() / 3600
        for name, lo, hi in HIST_BUCKETS:
            if h >= lo and (hi is None or h < hi):
                counts[name] += 1
                break
    return [{"bucket": b, "value": v} for b, v in counts.items()]


def _series(sub: list[Request], period: str, since: datetime, now: datetime) -> tuple[str, list[dict]]:
    """Dinamika: "bugun" — soatlar bo'yicha, boshqa davrlar — kunlar bo'yicha (Toshkent vaqti)."""
    def local(dt: datetime) -> datetime:
        return dt.replace(tzinfo=timezone.utc).astimezone(TASHKENT)
    if period == "today":
        hours = {h: 0 for h in range(local(now).hour + 1)}
        for r in sub:
            hours[local(r.created_at).hour] = hours.get(local(r.created_at).hour, 0) + 1
        return "hour", [{"label": f"{h:02d}:00", "value": v} for h, v in sorted(hours.items())]
    start, end = local(since).date(), local(now).date()
    days = {start + timedelta(days=i): 0 for i in range((end - start).days + 1)}
    for r in sub:
        d = local(r.created_at).date()
        if d in days:
            days[d] += 1
    return "day", [{"label": d.strftime("%d.%m"), "date": d.isoformat(), "value": v} for d, v in days.items()]


async def _scoped_rows(db: AsyncSession, actor: User, since: datetime) -> tuple[list[Request], list[District]]:
    s = access.scope(actor)
    q = select(Request).where(Request.created_at >= since, Request.status != RequestStatus.cancelled)
    dq = select(District).order_by(District.region_id, District.id)
    if s is not None:
        q = q.where(Request.district_id.in_(s or {-1}))
        dq = dq.where(District.id.in_(s or {-1}))
    return list((await db.execute(q)).scalars()), list((await db.execute(dq)).scalars())


async def detail(db: AsyncSession, actor: User, period: str, metric: str) -> dict:
    if metric not in METRICS:
        raise invalid("bad_metric", "Ko'rsatkich: " + ", ".join(METRICS))
    since = period_start(period)
    now = utcnow()
    rows, districts = await _scoped_rows(db, actor, since)
    sub = _subset(rows, metric, now)
    granularity, series = _series(sub, period, since, now)
    per = {d.id: 0 for d in districts}
    for r in sub:
        per[r.district_id] = per.get(r.district_id, 0) + 1
    return {"period": period, "metric": metric, "since": since, "value": len(sub), "granularity": granularity, "series": series,
            "composition": _composition(sub, metric, now), "histogram": _histogram(sub, now),
            "districts": [{"district_id": d.id, "name": d.name, "value": per.get(d.id, 0)} for d in districts]}
