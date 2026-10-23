"""GPS xodimi: smena ochish va haydovchi biriktirish (haydovchi modulini sinash uchun minimal to'plam)."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_roles
from app.core.errors import invalid
from app.models import User, Vehicle
from app.models.enums import Role
from app.repositories import requests as req_repo
from app.repositories import shifts as shift_repo
from app.schemas import AssignIn, RequestOut, ShiftOpenIn, ShiftOut, VehicleOut
from app.services import assignment_service, shift_service

router = APIRouter(prefix="/gps", tags=["gps"])
Gps = Depends(require_roles(Role.gps, Role.admin))


def _district(user: User, district_id: int | None) -> int:
    d = user.district_id or district_id
    if not d:
        raise invalid("district_required", "district_id kerak")
    return d


class DriverRow(BaseModel):
    id: int
    full_name: str
    phone: str | None
    shift: ShiftOut | None


@router.get("/drivers", response_model=list[DriverRow])
async def drivers(district_id: int | None = Query(None), user: User = Gps, db: AsyncSession = DB):
    d = _district(user, district_id)
    rows = (await db.execute(select(User).where(User.role == Role.driver, User.district_id == d, User.is_active))).scalars()
    shifts = {s.driver_id: s for s in await shift_repo.open_in_district(db, d)}
    return [DriverRow(id=u.id, full_name=u.full_name, phone=u.phone,
                      shift=ShiftOut.build(shifts[u.id]) if u.id in shifts else None) for u in rows]


@router.get("/vehicles", response_model=list[VehicleOut])
async def vehicles(district_id: int | None = Query(None), free: bool = True, user: User = Gps, db: AsyncSession = DB):
    d = _district(user, district_id)
    rows = list((await db.execute(select(Vehicle).where(Vehicle.district_id == d, Vehicle.is_active))).scalars())
    if free:
        busy = {s.vehicle_id for s in await shift_repo.open_in_district(db, d)}
        rows = [v for v in rows if v.id not in busy]
    return rows


@router.post("/shifts", response_model=ShiftOut, status_code=201)
async def open_shift(body: ShiftOpenIn, user: User = Gps, db: AsyncSession = DB):
    return ShiftOut.build(await shift_service.open_shift(db, user, body.driver_id, body.vehicle_id))


@router.get("/requests", response_model=list[RequestOut])
async def new_requests(district_id: int | None = Query(None), user: User = Gps, db: AsyncSession = DB):
    return await req_repo.new_in_district(db, user.district_id or district_id)


@router.post("/requests/{request_id}/assign", response_model=RequestOut)
async def assign(request_id: int, body: AssignIn, user: User = Gps, db: AsyncSession = DB):
    return await assignment_service.assign(db, user, request_id, body.driver_id)
