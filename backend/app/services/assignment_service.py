from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import conflict, forbidden, invalid, not_found
from app.db.base import utcnow
from app.models import Request, User
from app.models.enums import RequestStatus, Role, ShiftStatus
from app.repositories import requests as req_repo
from app.repositories import shifts as shift_repo
from app.services import events, naryad


async def assign(db: AsyncSession, gps_user: User, request_id: int, driver_id: int) -> Request:
    req = await req_repo.by_id(db, request_id, lock=True)
    if not req:
        raise not_found("request")
    if gps_user.district_id and gps_user.district_id != req.district_id:
        raise forbidden("Bu ariza sizning tumaningizga tegishli emas")
    if req.status != RequestStatus.new:
        raise conflict("request_not_new", "Ariza allaqachon biriktirilgan")
    # Korxona kartasi to'liq bo'lmasa (STIR yo'q yoki amaldagi shartnoma yo'q) — haydovchi yuborilmaydi
    missing = req.customer.missing_fields
    if missing:
        raise conflict("customer_incomplete", "Korxona ma'lumoti to'liq emas: " + ", ".join(missing))
    # Arizada shartnoma yo'q yoki muddati o'tgan bo'lsa — amaldagisi bog'lanadi (dalolatnomaga shu yoziladi)
    if req.contract is None or req.contract.customer_id != req.customer_id or not _in_force(req.contract):
        req.contract = req.customer.active_contract()
    driver = await db.get(User, driver_id)
    if not driver or driver.role != Role.driver or not driver.is_active:
        raise not_found("driver")
    if driver.district_id != req.district_id:
        raise invalid("district_mismatch", "Haydovchi faqat o'z tumanidagi arizaga biriktiriladi")
    shift = await shift_repo.open_for_driver(db, driver.id)
    if not shift or shift.status != ShiftStatus.active:
        raise conflict("driver_no_active_shift", "Haydovchida boshlangan smena yo'q")
    req.naryad_no = await naryad.next_number(db, req.district_id)
    req.driver_id = driver.id
    req.shift_id = shift.id
    req.status = RequestStatus.assigned
    req.assigned_at = utcnow()
    events.record(db, req, gps_user.id)
    await db.commit()
    await events.broadcast(req)
    return await req_repo.by_id(db, req.id)



def _in_force(contract) -> bool:
    today = date.today()
    return contract.is_active and contract.valid_from <= today <= contract.valid_to
