"""Call-center: arizalar, birinchi murojaatlar va statistika. Har amal ruxsat kodi bilan, tuman doirasida."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_perm
from app.models import User
from app.models.enums import AppealStatus, RequestStatus
from app.schemas import (AppealAcceptIn, AppealIn, AppealOut, ReasonIn, RequestCreateIn, RequestListOut, RequestPage,
                         StatsOut)
from app.services import callcenter as svc
from app.services import stats

router = APIRouter(tags=["call-center"])


def perm(*codes: str):
    return Depends(require_perm(*codes))


# --- arizalar ---
@router.get("/requests", response_model=RequestPage)
async def requests(district_id: int | None = None, status: RequestStatus | None = None, mine: bool = False, overdue: bool = False,
                   q: str | None = Query(None, max_length=100), limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                   user: User = perm("requests.view"), db: AsyncSession = DB):
    rows, total = await svc.list_requests(db, user, district_id=district_id, status=status, mine=mine, overdue=overdue, q=q,
                                          limit=limit, offset=offset)
    return RequestPage(items=[RequestListOut.model_validate(r) for r in rows], total=total)


@router.get("/requests/open", response_model=list[RequestListOut])
async def open_requests(customer_id: int, user: User = perm("requests.view", "requests.create"), db: AsyncSession = DB):
    """Korxonaning ochiq arizalari — operator yangi ariza ochishdan oldin "qayta ariza"ni tekshiradi."""
    return await svc.open_for_customer(db, user, customer_id)


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
@router.get("/stats/summary", response_model=StatsOut)
async def stats_summary(period: str = Query("today", pattern="^(today|month|last10|last5)$"), user: User = perm("stats.view"),
                        db: AsyncSession = DB):
    return await stats.summary(db, user, period)
