"""Admin ma'lumotnomalari: foydalanuvchilar ro'yxati, viloyatlar, tumanlar, mashinalar."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import District, Region, User, Vehicle
from app.models.enums import Role


async def list_users(db: AsyncSession, role: Role | None, district_id: int | None, active: bool | None) -> list[User]:
    q = select(User).order_by(User.role, User.district_id, User.username)
    if role:
        q = q.where(User.role == role)
    if district_id:
        q = q.where(User.district_id == district_id)
    if active is not None:
        q = q.where(User.is_active == active)
    return list((await db.execute(q)).scalars())


async def regions(db: AsyncSession) -> list[Region]:
    return list((await db.execute(select(Region).order_by(Region.id))).scalars())


async def districts(db: AsyncSession) -> list[District]:
    return list((await db.execute(select(District).order_by(District.region_id, District.id))).scalars())


async def vehicles(db: AsyncSession, district_id: int | None) -> list[Vehicle]:
    q = select(Vehicle).order_by(Vehicle.district_id, Vehicle.plate)
    if district_id:
        q = q.where(Vehicle.district_id == district_id)
    return list((await db.execute(q)).scalars())


async def vehicle_by_plate(db: AsyncSession, plate: str) -> Vehicle | None:
    return (await db.execute(select(Vehicle).where(Vehicle.plate == plate))).scalar_one_or_none()
