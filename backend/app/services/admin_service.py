"""Admin paneli qoidalari. O'chirish yo'q — faqat faolsizlantirish, tarix saqlanadi."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict, invalid, not_found
from app.core.security import hash_password
from app.models import AppSetting, District, Region, User, Vehicle
from app.models.enums import Role
from app.repositories import catalog
from app.repositories import settings as settings_repo
from app.repositories import shifts as shift_repo
from app.repositories import users as users_repo
from app.schemas import DistrictIn, DistrictUpdateIn, UserCreateIn, UserUpdateIn, VehicleIn, VehicleUpdateIn
from app.services.auth_service import check_password_strength

# Tumanga bog'lanishi shart bo'lgan rollar
DISTRICT_ROLES = {Role.driver, Role.gps}


async def _check_district(db: AsyncSession, role: Role, district_id: int | None) -> None:
    if role in DISTRICT_ROLES and not district_id:
        raise invalid("district_required", "Haydovchi va GPS xodimi tumanga biriktirilishi shart")
    if district_id:
        d = await db.get(District, district_id)
        if not d:
            raise not_found("district")
        if not d.is_active:
            raise invalid("district_inactive", "Bu tuman faolsizlantirilgan")


async def create_user(db: AsyncSession, body: UserCreateIn) -> User:
    if await users_repo.by_username(db, body.username):
        raise conflict("username_taken", "Bu login band")
    await _check_district(db, body.role, body.district_id)
    check_password_strength(body.password)
    user = User(username=body.username, full_name=body.full_name.strip(), phone=body.phone, role=body.role,
                district_id=body.district_id, language=body.language, password_hash=hash_password(body.password),
                must_change_password=True)
    db.add(user)
    await db.commit()
    return user


async def update_user(db: AsyncSession, admin: User, user_id: int, body: UserUpdateIn) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise not_found("user")
    data = body.model_dump(exclude_unset=True)
    if user.id == admin.id and (data.get("is_active") is False or data.get("role", Role.admin) != Role.admin):
        raise conflict("cannot_change_self", "O'zingizni faolsizlantira yoki rolingizni o'zgartira olmaysiz")
    role = data.get("role", user.role)
    district_id = data["district_id"] if "district_id" in data else user.district_id
    if "role" in data or "district_id" in data:
        await _check_district(db, role, district_id)
    if user.role == Role.driver and (data.get("is_active") is False or "district_id" in data or role != Role.driver):
        if await shift_repo.open_for_driver(db, user.id):
            raise conflict("driver_has_open_shift", "Haydovchida ochiq smena bor — avval smenani yoping")
    for key, value in data.items():
        setattr(user, key, value.strip() if key == "full_name" and value else value)
    await db.commit()
    return user


async def reset_password(db: AsyncSession, user_id: int, password: str) -> User:
    user = await db.get(User, user_id)
    if not user:
        raise not_found("user")
    check_password_strength(password)
    user.password_hash = hash_password(password)
    user.must_change_password = True
    user.failed_logins = 0
    user.locked_until = None  # blokdan chiqarish ham shu yerda
    await db.commit()
    return user


async def create_district(db: AsyncSession, body: DistrictIn) -> District:
    if not await db.get(Region, body.region_id):
        raise not_found("region")
    d = District(name=body.name.strip(), region_id=body.region_id)
    db.add(d)
    await db.commit()
    return d


async def update_district(db: AsyncSession, district_id: int, body: DistrictUpdateIn) -> District:
    d = await db.get(District, district_id)
    if not d:
        raise not_found("district")
    data = body.model_dump(exclude_unset=True)
    if data.get("is_active") is False and await shift_repo.open_in_district(db, d.id):
        raise conflict("district_has_open_shifts", "Tumanda ochiq smenalar bor")
    if "name" in data:
        d.name = data["name"].strip()
    if "is_active" in data:
        d.is_active = data["is_active"]
    await db.commit()
    return d




def normalize_plate(plate: str) -> str:
    """'60 a123bc' → '60 A123BC': katta harf, ortiqcha bo'shliqlarsiz."""
    return " ".join(plate.upper().split())


async def create_vehicle(db: AsyncSession, body: VehicleIn) -> Vehicle:
    plate = normalize_plate(body.plate)
    if await catalog.vehicle_by_plate(db, plate):
        raise conflict("plate_taken", "Bu davlat raqami allaqachon bor")
    await _check_district(db, Role.admin, body.district_id)
    v = Vehicle(plate=plate, model=body.model, district_id=body.district_id)
    db.add(v)
    await db.commit()
    return v


async def update_vehicle(db: AsyncSession, vehicle_id: int, body: VehicleUpdateIn) -> Vehicle:
    v = await db.get(Vehicle, vehicle_id)
    if not v:
        raise not_found("vehicle")
    data = body.model_dump(exclude_unset=True)
    if "plate" in data:
        plate = normalize_plate(data["plate"])
        other = await catalog.vehicle_by_plate(db, plate)
        if other and other.id != v.id:
            raise conflict("plate_taken", "Bu davlat raqami allaqachon bor")
        data["plate"] = plate
    if (data.get("is_active") is False or "district_id" in data) and await shift_repo.open_for_vehicle(db, v.id):
        raise conflict("vehicle_busy", "Mashina ochiq smenada — avval smenani yoping")
    if "district_id" in data:
        await _check_district(db, Role.admin, data["district_id"])
    for key, value in data.items():
        setattr(v, key, value)
    await db.commit()
    return v


async def set_gps_radius(db: AsyncSession, value: int) -> int:
    row = await db.get(AppSetting, settings_repo.GPS_RADIUS)
    if row:
        row.value = str(value)
    else:
        db.add(AppSetting(key=settings_repo.GPS_RADIUS, value=str(value)))
    await db.commit()
    return await settings_repo.gps_radius(db)
