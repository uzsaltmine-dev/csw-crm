from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Shift
from app.models.enums import ShiftStatus

OPEN_STATES = (ShiftStatus.opened, ShiftStatus.active)


async def by_id(db: AsyncSession, shift_id: int) -> Shift | None:
    q = select(Shift).where(Shift.id == shift_id).options(selectinload(Shift.vehicle), selectinload(Shift.driver))
    return (await db.execute(q)).scalar_one_or_none()


async def open_for_driver(db: AsyncSession, driver_id: int) -> Shift | None:
    q = (select(Shift).where(Shift.driver_id == driver_id, Shift.status.in_(OPEN_STATES))
         .options(selectinload(Shift.vehicle)).order_by(Shift.id.desc()))
    return (await db.execute(q)).scalars().first()


async def open_for_vehicle(db: AsyncSession, vehicle_id: int) -> Shift | None:
    q = select(Shift).where(Shift.vehicle_id == vehicle_id, Shift.status.in_(OPEN_STATES))
    return (await db.execute(q)).scalars().first()


async def open_in_district(db: AsyncSession, district_id: int) -> list[Shift]:
    q = (select(Shift).where(Shift.district_id == district_id, Shift.status.in_(OPEN_STATES))
         .options(selectinload(Shift.vehicle), selectinload(Shift.driver)))
    return list((await db.execute(q)).scalars())
