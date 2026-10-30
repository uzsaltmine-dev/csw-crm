"""Kunlik ish jadvali va mashina joylashuvi.

GPS xodimi har kuni tumani uchun mashinalarni haydovchi va xizmat turi (yuridik bo'lim yoki jismoniy abonentlar — mahallalar)
bilan biriktiradi. Mashina biriktirilganda arizaning haydovchisi shu jadvaldan olinadi.
Kelajakdagi GPS-monitoring tizimi jadvalni va mashina joylashuvini integratsiya API'si orqali o'qiydi va yozadi.
"""
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import conflict, invalid, not_found
from app.db.base import utcnow
from app.models import Customer, Request, User, Vehicle, VehiclePosition, WorkSchedule
from app.models.enums import Role
from app.services import access
from app.services.geo import distance_m, valid_coords

SERVICES = ("legal", "individual")
TASHKENT = timezone(timedelta(hours=5))


def today() -> date:
    return utcnow().replace(tzinfo=timezone.utc).astimezone(TASHKENT).date()


async def day_rows(db: AsyncSession, district_id: int, day: date) -> list[WorkSchedule]:
    q = (select(WorkSchedule).where(WorkSchedule.district_id == district_id, WorkSchedule.day == day)
         .options(selectinload(WorkSchedule.vehicle), selectinload(WorkSchedule.driver)).order_by(WorkSchedule.id))
    return list((await db.execute(q)).scalars())


def row_out(r: WorkSchedule) -> dict:
    return {"id": r.id, "day": r.day, "district_id": r.district_id, "vehicle_id": r.vehicle_id, "plate": r.vehicle.plate,
            "model": r.vehicle.model, "driver_id": r.driver_id, "driver_name": r.driver.full_name if r.driver else None,
            "service": r.service, "mahallas": r.mahallas}


async def save_day(db: AsyncSession, actor: User | None, district_id: int, day: date, rows: list[dict]) -> list[WorkSchedule]:
    """Kunning jadvalini to'liq almashtiradi. Har mashina va har haydovchi kuniga bir marta."""
    vehicles = {v.id: v for v in (await db.execute(select(Vehicle).where(Vehicle.district_id == district_id))).scalars()}
    drivers = {u.id: u for u in (await db.execute(select(User).where(User.role == Role.driver, User.district_id == district_id))).scalars()}
    seen_v, seen_d = set(), set()
    for r in rows:
        v = vehicles.get(r["vehicle_id"])
        if not v or not v.is_active:
            raise invalid("bad_vehicle", "Mashina shu tumanga tegishli emas yoki faol emas")
        if r["vehicle_id"] in seen_v:
            raise conflict("vehicle_twice", f"{v.plate} jadvalda ikki marta")
        seen_v.add(r["vehicle_id"])
        d = r.get("driver_id")
        if d is not None:
            if d not in drivers or not drivers[d].is_active:
                raise invalid("bad_driver", "Haydovchi shu tumanga tegishli emas yoki faol emas")
            if d in seen_d:
                raise conflict("driver_twice", f"{drivers[d].full_name} bir kunda ikki mashinada")
            seen_d.add(d)
        if r.get("service", "legal") not in SERVICES:
            raise invalid("bad_service", "Xizmat turi: legal yoki individual")
    await db.execute(delete(WorkSchedule).where(WorkSchedule.district_id == district_id, WorkSchedule.day == day))
    for r in rows:
        db.add(WorkSchedule(day=day, district_id=district_id, vehicle_id=r["vehicle_id"], driver_id=r.get("driver_id"),
                            service=r.get("service", "legal"), mahallas=(r.get("mahallas") or "").strip() or None,
                            created_by_id=actor.id if actor else None))
    await db.commit()
    return await day_rows(db, district_id, day)


async def copy_day(db: AsyncSession, actor: User, district_id: int, day: date, from_day: date) -> list[WorkSchedule]:
    src = await day_rows(db, district_id, from_day)
    if not src:
        raise not_found("schedule")
    return await save_day(db, actor, district_id, day, [
        {"vehicle_id": r.vehicle_id, "driver_id": r.driver_id, "service": r.service, "mahallas": r.mahallas}
        for r in src if r.vehicle.is_active])


async def for_vehicle_today(db: AsyncSession, vehicle_id: int) -> WorkSchedule | None:
    q = select(WorkSchedule).where(WorkSchedule.vehicle_id == vehicle_id, WorkSchedule.day == today()) \
        .options(selectinload(WorkSchedule.driver), selectinload(WorkSchedule.vehicle))
    return (await db.execute(q)).scalar_one_or_none()


async def for_driver_today(db: AsyncSession, driver_id: int) -> WorkSchedule | None:
    q = select(WorkSchedule).where(WorkSchedule.driver_id == driver_id, WorkSchedule.day == today()) \
        .options(selectinload(WorkSchedule.vehicle))
    return (await db.execute(q)).scalars().first()


# --- mashina joylashuvi ---
async def set_position(db: AsyncSession, vehicle_id: int, lat: float, lng: float, at: datetime | None, source: str) -> None:
    if not valid_coords(lat, lng):
        raise invalid("bad_coords", "Koordinatalar noto'g'ri")
    at = (at.astimezone(timezone.utc).replace(tzinfo=None) if at and at.tzinfo else at) or utcnow()
    row = await db.get(VehiclePosition, vehicle_id)
    if row is None:
        db.add(VehiclePosition(vehicle_id=vehicle_id, lat=lat, lng=lng, at=at, source=source))
    elif at >= row.at:
        row.lat, row.lng, row.at, row.source = lat, lng, at, source


async def vehicle_options(db: AsyncSession, user: User, request_id: int) -> dict:
    """Qizil kartadagi mashina dropdowni: tuman mashinalari, bugun yuridik bo'lim uchun ishlayotganlar yuqorida,
    ichida korxonagacha masofa bo'yicha (joylashuv yo'q bo'lsa — oxirida)."""
    req = await db.get(Request, request_id)
    if not req:
        raise not_found("request")
    access.check_scope(user, req.district_id)
    cust = await db.get(Customer, req.customer_id)
    vehicles = list((await db.execute(select(Vehicle).where(Vehicle.district_id == req.district_id, Vehicle.is_active)
                                      .order_by(Vehicle.plate))).scalars())
    sched = {r.vehicle_id: r for r in await day_rows(db, req.district_id, today())}
    pos = {p.vehicle_id: p for p in (await db.execute(select(VehiclePosition).where(
        VehiclePosition.vehicle_id.in_([v.id for v in vehicles] or [-1])))).scalars()}
    has_loc = cust is not None and cust.lat is not None and cust.lng is not None
    out = []
    for v in vehicles:
        s, p = sched.get(v.id), pos.get(v.id)
        dist = distance_m(cust.lat, cust.lng, p.lat, p.lng) if has_loc and p else None
        out.append({"vehicle_id": v.id, "plate": v.plate, "model": v.model, "service": s.service if s else None,
                    "driver_id": s.driver_id if s else None, "driver_name": s.driver.full_name if s and s.driver else None,
                    "distance_m": dist, "position_at": p.at if p else None, "position_source": p.source if p else None,
                    "available": bool(s and s.driver_id)})
    rank = {"legal": 0, "individual": 1, None: 2}
    out.sort(key=lambda x: (rank[x["service"]], x["distance_m"] is None, x["distance_m"] or 0, x["plate"]))
    return {"request_id": req.id, "customer_has_location": has_loc, "items": out}
