"""Korxona kartasi: yaratish, tahrirlash, aloqalar, shartnomalar, koordinatani tasdiqlash."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict, forbidden, invalid, not_found
from app.models import Contract, Customer, CustomerContact, District, User
from app.models.enums import LocationStatus, Role
from app.repositories import customers as repo
from app.schemas import (
    ContactIn,
    ContractIn,
    CustomerIn,
    CustomerUpdateIn,
    LocationConfirmIn,
)
from app.services.customer_import import next_fixed_no_start
from app.services.geo import valid_coords
from app.services.normalize import format_phone, key, phone_digits


def check_district_access(user: User, district_id: int) -> None:
    """Tumanga bog'langan xodim (GPS) faqat o'z tumanini ko'radi."""
    if user.role == Role.gps and user.district_id != district_id:
        raise forbidden("Bu korxona sizning tumaningizga tegishli emas")


async def _load(db: AsyncSession, customer_id: int, lock: bool = False) -> Customer:
    cust = await repo.get(db, customer_id, lock=lock)
    if not cust:
        raise not_found("customer")
    return cust


async def _check_stir(db: AsyncSession, stir: str | None, own_id: int | None = None) -> None:
    if stir:
        other = await repo.by_stir(db, stir)
        if other and other.id != own_id:
            raise conflict("stir_taken", f"Bu STIR {other.fixed_no} korxonasida bor")


async def _check_name(db: AsyncSession, district_id: int, name: str, own_id: int | None = None) -> str:
    k = key(name)
    if not k:
        raise invalid("bad_name", "Korxona nomi noto'g'ri")
    other = await repo.by_name_key(db, district_id, k)
    if other and other.id != own_id:
        raise conflict("customer_exists", f"Bu tumanda shu nomli korxona bor: {other.fixed_no}")
    return k


async def create(db: AsyncSession, body: CustomerIn) -> Customer:
    district = await db.get(District, body.district_id)
    if not district or not district.is_active:
        raise not_found("district")
    name_key = await _check_name(db, body.district_id, body.name)
    await _check_stir(db, body.stir)
    cust = Customer(fixed_no=f"A-{await next_fixed_no_start(db):04d}", name=body.name.strip(), name_key=name_key,
                    district_id=body.district_id, stir=body.stir, director=body.director, address=body.address,
                    activity_type=body.activity_type, phone=format_phone(body.phone), source="manual",
                    location_status=LocationStatus.none)
    db.add(cust)
    await db.commit()
    return await _load(db, cust.id)


async def update(db: AsyncSession, customer_id: int, body: CustomerUpdateIn) -> Customer:
    cust = await _load(db, customer_id, lock=True)
    data = body.model_dump(exclude_unset=True)
    if data.get("name"):
        cust.name_key = await _check_name(db, cust.district_id, data["name"], cust.id)
        cust.name = data["name"].strip()
    if "stir" in data:
        await _check_stir(db, data["stir"], cust.id)
        cust.stir = data["stir"]
    if "phone" in data:
        cust.phone = format_phone(data["phone"])
    for f in ("director", "address", "activity_type"):
        if f in data:
            setattr(cust, f, (data[f] or "").strip() or None)
    await db.commit()
    return await _load(db, cust.id)


async def add_contact(db: AsyncSession, customer_id: int, body: ContactIn) -> Customer:
    cust = await _load(db, customer_id, lock=True)
    if len(phone_digits(body.phone)) != 9:
        raise invalid("bad_phone", "Telefon raqami 9 xonali bo'lishi kerak (masalan, 94 512 11 16)")
    phone = format_phone(body.phone)
    if any(c.phone == phone for c in cust.contacts):
        raise conflict("contact_exists", "Bu raqam allaqachon bor")
    cust.contacts.append(CustomerContact(name=(body.name or "").strip() or None, phone=phone))
    cust.phone = cust.phone or phone
    await db.commit()
    return await _load(db, cust.id)


async def add_contract(db: AsyncSession, customer_id: int, body: ContractIn) -> Customer:
    cust = await _load(db, customer_id, lock=True)
    if body.valid_to < body.valid_from:
        raise invalid("bad_dates", "Tugash sanasi boshlanish sanasidan oldin bo'lmasin")
    number = body.number.strip()
    if await repo.contract_by_number(db, number):
        raise conflict("contract_number_taken", "Bu raqamli shartnoma bor")
    db.add(Contract(customer_id=cust.id, number=number, type=body.type, signed_on=body.signed_on, price=body.price,
                    valid_from=body.valid_from, valid_to=body.valid_to, is_active=True))
    await db.commit()
    return await _load(db, cust.id)


async def confirm_location(db: AsyncSession, customer_id: int, body: LocationConfirmIn) -> Customer:
    cust = await _load(db, customer_id, lock=True)
    if (body.lat is None) != (body.lng is None):
        raise invalid("bad_coords", "lat va lng birga beriladi")
    if body.lat is not None:
        if not valid_coords(body.lat, body.lng):
            raise invalid("bad_coords", "Koordinatalar noto'g'ri")
        cust.lat, cust.lng = body.lat, body.lng
    elif cust.lat is None or cust.lng is None:
        raise conflict("no_location", "Tasdiqlash uchun koordinata yo'q — birinchi tashrifni kuting yoki qo'lda kiriting")
    cust.location_status = LocationStatus.confirmed
    await db.commit()
    return await _load(db, cust.id)
