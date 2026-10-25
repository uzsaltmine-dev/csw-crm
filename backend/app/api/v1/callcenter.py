"""Call-center: arizalar, birinchi murojaatlar va statistika. Har amal ruxsat kodi bilan, tuman doirasida."""
from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, Query, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_perm
from app.db.base import utcnow
from app.models import User
from app.models.enums import AppealStatus, RequestStatus, WasteType
from app.repositories import requests as req_repo
from app.schemas import (AppealAcceptIn, AppealIn, AppealOut, ReasonIn, RequestCreateIn, RequestDetailOut, RequestEventOut,
                         RequestListOut, RequestPage, SeenIn, StatsOut)
from app.services import callcenter as svc
from app.services import stats
from app.services import stats_export as exporter

router = APIRouter(tags=["call-center"])


def perm(*codes: str):
    return Depends(require_perm(*codes))


# --- arizalar ---
def _local_day(d: date | None, plus_days: int = 0) -> datetime | None:
    """Toshkent sanasi → UTC (bazadagi vaqt)."""
    if d is None:
        return None
    return datetime.combine(d + timedelta(days=plus_days), time.min) - timedelta(hours=5)


@router.get("/requests", response_model=RequestPage)
async def requests(district_id: int | None = None, status: RequestStatus | None = None, mine: bool = False, overdue: bool = False,
                   repeat: bool = False, waste_type: WasteType | None = None, date_from: date | None = None, date_to: date | None = None,
                   q: str | None = Query(None, max_length=100), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                   user: User = perm("requests.view"), db: AsyncSession = DB):
    rows, total = await svc.list_requests(db, user, district_id=district_id, status=status, mine=mine, overdue=overdue, q=q,
                                          limit=limit, offset=offset, date_from=_local_day(date_from), date_to=_local_day(date_to, 1),
                                          waste_type=waste_type, repeat=repeat)
    seen = await req_repo.seen_ids(db, user.id, [r.id for r in rows])
    items = []
    for r in rows:
        item = RequestListOut.model_validate(r)
        item.seen = r.id in seen
        items.append(item)
    return RequestPage(items=items, total=total)


@router.post("/requests/seen", status_code=204)
async def mark_seen(body: SeenIn, user: User = perm("requests.view"), db: AsyncSession = DB):
    """"Yangi" belgisini olib tashlash (xodim arizani ko'rdi)."""
    await req_repo.mark_seen(db, user.id, body.request_ids)


@router.get("/requests/open", response_model=list[RequestListOut])
async def open_requests(customer_id: int, user: User = perm("requests.view", "requests.create"), db: AsyncSession = DB):
    """Korxonaning ochiq arizalari — operator yangi ariza ochishdan oldin "qayta ariza"ni tekshiradi."""
    return await svc.open_for_customer(db, user, customer_id)


@router.get("/requests/{request_id}", response_model=RequestDetailOut)
async def request_detail(request_id: int, user: User = perm("requests.view"), db: AsyncSession = DB):
    d = await svc.request_detail(db, user, request_id)
    out = RequestDetailOut.model_validate(d["req"])
    out.driver_name, out.created_by_name, out.seen = d["driver_name"], d["created_by_name"], True
    out.events = [RequestEventOut(**e) for e in d["events"]]
    return out


@router.post("/requests", response_model=RequestListOut, status_code=201)
async def create_request(body: RequestCreateIn, user: User = perm("requests.create"), db: AsyncSession = DB):
    return await svc.create_request(db, user, body)


@router.post("/requests/{request_id}/cancel", response_model=RequestListOut)
async def cancel_request(request_id: int, body: ReasonIn, user: User = perm("requests.cancel"), db: AsyncSession = DB):
    return await svc.cancel_request(db, user, request_id, body.reason)


# --- birinchi murojaatlar ---
@router.get("/appeals", response_model=list[AppealOut])
async def appeals(status: AppealStatus | None = None, mine: bool = False, user: User = perm("appeals.view"), db: AsyncSession = DB):
    return await svc.list_appeals(db, user, status, mine)


@router.post("/appeals", response_model=AppealOut, status_code=201)
async def create_appeal(body: AppealIn, user: User = perm("appeals.create"), db: AsyncSession = DB):
    return await svc.create_appeal(db, user, body)


@router.post("/appeals/{appeal_id}/accept", response_model=AppealOut)
async def accept_appeal(appeal_id: int, body: AppealAcceptIn, user: User = perm("appeals.review"), db: AsyncSession = DB):
    return await svc.accept_appeal(db, user, appeal_id, body)


@router.post("/appeals/{appeal_id}/reject", response_model=AppealOut)
async def reject_appeal(appeal_id: int, body: ReasonIn, user: User = perm("appeals.review"), db: AsyncSession = DB):
    return await svc.reject_appeal(db, user, appeal_id, body.reason)


# --- statistika ---
PERIOD = Query("today", pattern="^(today|month|last10|last5)$")
METRIC = Query("received", pattern="^(received|repeat|pending|overdue|done|not_done)$")


@router.get("/stats/summary", response_model=StatsOut)
async def stats_summary(period: str = PERIOD, user: User = perm("stats.view"), db: AsyncSession = DB):
    return await stats.summary(db, user, period)


@router.get("/stats/detail")
async def stats_detail(period: str = PERIOD, metric: str = METRIC, user: User = perm("stats.view"), db: AsyncSession = DB) -> dict:
    """Tanlangan ko'rsatkich: dinamika (area), tarkib (pie), vaqt taqsimoti (histogramma), tumanlar (bar)."""
    return await stats.detail(db, user, period, metric)


@router.get("/stats/export")
async def stats_export(period: str = PERIOD, metric: str = METRIC, format: str = Query("xlsx", pattern="^(xlsx|pdf)$"),
                       user: User = perm("stats.view"), db: AsyncSession = DB) -> Response:
    """Excel yoki PDF — tanlangan davr va ko'rsatkich bo'yicha."""
    s = await stats.summary(db, user, period)
    d = await stats.detail(db, user, period, metric)
    content = await run_in_threadpool(exporter.to_xlsx if format == "xlsx" else exporter.to_pdf, s, d)
    media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if format == "xlsx" else "application/pdf"
    name = f"statistika-{period}-{metric}-{utcnow().strftime('%Y%m%d-%H%M')}.{format}"
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{name}"'})
