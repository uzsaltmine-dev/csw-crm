"""Korxonalar: qidiruv, filtrlar, sahifalash."""
from datetime import date

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Contract, Customer, CustomerContact, ImportBatch
from app.models.enums import LocationStatus
from app.services.normalize import format_phone, key, phone_digits


def _active_contract_exists(today: date):
    return exists().where(and_(Contract.customer_id == Customer.id, Contract.is_active,
                               Contract.valid_from <= today, Contract.valid_to >= today))


async def search(db: AsyncSession, *, district_id: int | None, q: str | None, incomplete: bool, location: LocationStatus | None,
                 limit: int, offset: int, scope: set[int] | None = None) -> tuple[list[Customer], int, dict[int, int]]:
    cond = []
    if district_id:
        cond.append(Customer.district_id == district_id)
    if scope is not None:  # admin emas — faqat o'z tumanlari
        cond.append(Customer.district_id.in_(scope or {-1}))
    if q and q.strip():
        text = q.strip()
        digits = phone_digits(text)
        like = [Customer.name_key.contains(key(text)), Customer.fixed_no == text.upper()]
        if digits:
            like.append(Customer.stir.contains(digits))
            if len(digits) == 9:  # to'liq telefon raqami
                phone = format_phone(digits)
                like += [Customer.phone == phone,
                         Customer.id.in_(select(CustomerContact.customer_id).where(CustomerContact.phone == phone))]
        cond.append(or_(*like))
    if incomplete:
        cond.append(or_(Customer.stir.is_(None), ~_active_contract_exists(date.today())))
    if location:
        cond.append(Customer.location_status == location)
    total = (await db.execute(select(func.count()).select_from(Customer).where(*cond))).scalar_one()
    rows = list((await db.execute(
        select(Customer).where(*cond).options(selectinload(Customer.contracts))
        .order_by(Customer.district_id, Customer.name).limit(limit).offset(offset))).scalars())
    counts = dict((await db.execute(
        select(CustomerContact.customer_id, func.count()).where(CustomerContact.customer_id.in_([c.id for c in rows]))
        .group_by(CustomerContact.customer_id))).all()) if rows else {}
    return rows, total, counts


async def get(db: AsyncSession, customer_id: int, lock: bool = False) -> Customer | None:
    q = (select(Customer).where(Customer.id == customer_id)
         .options(selectinload(Customer.contacts), selectinload(Customer.contracts))
         .execution_options(populate_existing=True))
    if lock:
        q = q.with_for_update()
    return (await db.execute(q)).scalar_one_or_none()


async def by_stir(db: AsyncSession, stir: str) -> Customer | None:
    return (await db.execute(select(Customer).where(Customer.stir == stir))).scalar_one_or_none()


async def by_name_key(db: AsyncSession, district_id: int, name_key: str) -> Customer | None:
    return (await db.execute(select(Customer).where(Customer.district_id == district_id,
                                                    Customer.name_key == name_key))).scalar_one_or_none()


async def contract_by_number(db: AsyncSession, number: str) -> Contract | None:
    return (await db.execute(select(Contract).where(Contract.number == number))).scalar_one_or_none()


async def import_batches(db: AsyncSession, limit: int = 50) -> list[ImportBatch]:
    return list((await db.execute(select(ImportBatch).order_by(ImportBatch.id.desc()).limit(limit))).scalars())
