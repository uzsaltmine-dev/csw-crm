from decimal import Decimal
from uuid import uuid4

from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, conflict, forbidden, invalid, not_found
from app.db.base import utcnow
from app.models import Shift, User, Vehicle
from app.models.enums import Role, ShiftStatus
from app.repositories import requests as req_repo
from app.repositories import shifts as shift_repo
from app.services.files import UploadedImage
from app.services.storage import Storage


async def open_shift(db: AsyncSession, gps_user: User, driver_id: int, vehicle_id: int) -> Shift:
    driver = await db.get(User, driver_id)
    vehicle = await db.get(Vehicle, vehicle_id)
    if not driver or driver.role != Role.driver or not driver.is_active:
        raise not_found("driver")
    if not vehicle or not vehicle.is_active:
        raise not_found("vehicle")
    if gps_user.district_id and gps_user.district_id != driver.district_id:
        raise forbidden("Faqat o'z tumaningiz haydovchilariga smena ochasiz")
    if driver.district_id != vehicle.district_id:
        raise invalid("district_mismatch", "Haydovchi va mashina bitta tumanga tegishli bo'lishi kerak")
    if await shift_repo.open_for_driver(db, driver.id):
        raise conflict("driver_has_open_shift", "Haydovchida ochiq smena bor")
    if await shift_repo.open_for_vehicle(db, vehicle.id):
        raise conflict("vehicle_busy", "Bu mashina boshqa ochiq smenada")
    shift = Shift(driver_id=driver.id, vehicle_id=vehicle.id, district_id=driver.district_id, opened_by_id=gps_user.id)
    db.add(shift)
    await db.commit()
    return await shift_repo.by_id(db, shift.id)


async def _own_shift(db: AsyncSession, driver: User, shift_id: int) -> Shift:
    shift = await shift_repo.by_id(db, shift_id)
    if not shift or shift.driver_id != driver.id:
        raise not_found("shift")
    return shift


async def start_shift(db: AsyncSession, storage: Storage, driver: User, shift_id: int,
                      odometer: int, fuel: Decimal, photo: UploadedImage) -> Shift:
    shift = await _own_shift(db, driver, shift_id)
    if shift.status != ShiftStatus.opened:
        raise conflict("shift_not_opened", "Smena allaqachon boshlangan yoki yopilgan")
    if odometer < 0 or fuel < 0:
        raise invalid("bad_reading", "Spidometr va yoqilg'i manfiy bo'lishi mumkin emas")
    key = f"shifts/{shift.id}/vehicle-{uuid4().hex}.{photo.ext}"
    await run_in_threadpool(storage.put, key, photo.data, photo.content_type)
    shift.vehicle_photo_key = key
    shift.odometer_start = odometer
    shift.fuel_start = fuel
    shift.started_at = utcnow()
    shift.status = ShiftStatus.active
    await db.commit()
    return await shift_repo.by_id(db, shift.id)


async def end_shift(db: AsyncSession, driver: User, shift_id: int, odometer: int, fuel: Decimal) -> Shift:
    shift = await _own_shift(db, driver, shift_id)
    if shift.status != ShiftStatus.active:
        raise conflict("shift_not_active", "Faqat boshlangan smenani yopish mumkin")
    if odometer < (shift.odometer_start or 0):
        raise invalid("odometer_decreased", "Smena oxiridagi spidometr boshidagidan kichik bo'lishi mumkin emas")
    if fuel < 0:
        raise invalid("bad_reading", "Yoqilg'i manfiy bo'lishi mumkin emas")
    if await req_repo.count_active_on_shift(db, shift.id):
        raise conflict("shift_has_active_requests", "Smenada yakunlanmagan arizalar bor")
    shift.odometer_end = odometer
    shift.fuel_end = fuel
    shift.ended_at = utcnow()
    shift.status = ShiftStatus.closed
    await db.commit()
    return await shift_repo.by_id(db, shift.id)
