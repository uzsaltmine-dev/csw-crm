"""Tashqi tizimlar uchun API (GPS-monitoring): mashina joylashuvi va kunlik ish jadvali. X-Api-Key bilan.
INTEGRATION_API_KEY sozlanmagan bo'lsa — o'chiq (503)."""
import hmac
from datetime import date, datetime

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB
from app.core.config import get_settings
from app.core.errors import AppError
from app.models import Vehicle
from app.services import schedule

router = APIRouter(prefix="/integrations", tags=["integrations"])


async def api_key(x_api_key: str | None = Header(None)) -> None:
    key = get_settings().integration_api_key
    if not key:
        raise AppError(503, "integration_disabled", "Integratsiya API'si sozlanmagan (INTEGRATION_API_KEY)")
    if not x_api_key or not hmac.compare_digest(x_api_key, key):
        raise AppError(401, "bad_api_key", "API kalit noto'g'ri")


Key = Depends(api_key)


class PositionIn(BaseModel):
    plate: str | None = Field(None, max_length=20)
    vehicle_id: int | None = None
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    at: datetime | None = None


class PositionsIn(BaseModel):
    positions: list[PositionIn] = Field(max_length=1000)


@router.post("/vehicle-positions")
async def vehicle_positions(body: PositionsIn, _: None = Key, db: AsyncSession = DB) -> dict:
    """Mashinalarning oxirgi joylashuvi (davlat raqami yoki id bo'yicha). Noma'lum mashinalar o'tkazib yuboriladi."""
    vehicles = list((await db.execute(select(Vehicle))).scalars())
    by_plate = {v.plate.replace(" ", "").upper(): v.id for v in vehicles}
    ids = {v.id for v in vehicles}
    saved, unknown = 0, []
    for p in body.positions:
        vid = p.vehicle_id if p.vehicle_id in ids else by_plate.get((p.plate or "").replace(" ", "").upper())
        if not vid:
            unknown.append(p.plate or p.vehicle_id)
            continue
        await schedule.set_position(db, vid, p.lat, p.lng, p.at, "monitoring")
        saved += 1
    await db.commit()
    return {"saved": saved, "unknown": unknown}


@router.get("/schedule")
async def get_schedule(district_id: int, day: date | None = None, _: None = Key, db: AsyncSession = DB) -> list[dict]:
    return [schedule.row_out(r) for r in await schedule.day_rows(db, district_id, day or schedule.today())]


class RowIn(BaseModel):
    vehicle_id: int
    driver_id: int | None = None
    service: str = Field("legal", pattern="^(legal|individual)$")
    mahallas: str | None = Field(None, max_length=500)


@router.put("/schedule")
async def put_schedule(district_id: int, rows: list[RowIn], day: date | None = None, _: None = Key, db: AsyncSession = DB) -> list[dict]:
    saved = await schedule.save_day(db, None, district_id, day or schedule.today(), [r.model_dump() for r in rows])
    return [schedule.row_out(r) for r in saved]
