"""Korxonalar bazasi.

O'qish: admin, manager, yuridik bo'lim, GPS xodimi (faqat o'z tumani).
Karta va shartnoma: admin va yuridik bo'lim xodimi. Koordinatani tasdiqlash: admin va manager.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_roles
from app.core.errors import not_found
from app.models import User
from app.models.enums import LocationStatus, Role
from app.repositories import customers as repo
from app.schemas import (
    ContactIn,
    ContractIn,
    CustomerDetailOut,
    CustomerIn,
    CustomerListOut,
    CustomerPage,
    CustomerUpdateIn,
    LocationConfirmIn,
)
from app.services import customer_service as svc

router = APIRouter(prefix="/customers", tags=["customers"])
Reader = Depends(require_roles(Role.admin, Role.manager, Role.legal, Role.gps))
Editor = Depends(require_roles(Role.admin, Role.legal))
Confirmer = Depends(require_roles(Role.admin, Role.manager))


def _detail(c) -> CustomerDetailOut:
    out = CustomerDetailOut.model_validate(c)
    out.contacts_count = len(c.contacts)
    return out


@router.get("", response_model=CustomerPage)
async def search(district_id: int | None = None, q: str | None = Query(None, max_length=100), incomplete: bool = False,
                 location: LocationStatus | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 user: User = Reader, db: AsyncSession = DB):
    if user.role == Role.gps:
        district_id = user.district_id
    rows, total, counts = await repo.search(db, district_id=district_id, q=q, incomplete=incomplete, location=location,
                                            limit=limit, offset=offset)
    items = []
    for c in rows:
        item = CustomerListOut.model_validate(c)
        item.contacts_count = counts.get(c.id, 0)
        items.append(item)
    return CustomerPage(items=items, total=total)


@router.post("", response_model=CustomerDetailOut, status_code=201)
async def create(body: CustomerIn, _: User = Editor, db: AsyncSession = DB):
    return _detail(await svc.create(db, body))


@router.get("/{customer_id}", response_model=CustomerDetailOut)
async def detail(customer_id: int, user: User = Reader, db: AsyncSession = DB):
    cust = await repo.get(db, customer_id)
    if not cust:
        raise not_found("customer")
    svc.check_district_access(user, cust.district_id)
    return _detail(cust)


@router.patch("/{customer_id}", response_model=CustomerDetailOut)
async def update(customer_id: int, body: CustomerUpdateIn, _: User = Editor, db: AsyncSession = DB):
    return _detail(await svc.update(db, customer_id, body))


@router.post("/{customer_id}/contacts", response_model=CustomerDetailOut, status_code=201)
async def add_contact(customer_id: int, body: ContactIn, _: User = Editor, db: AsyncSession = DB):
    return _detail(await svc.add_contact(db, customer_id, body))


@router.post("/{customer_id}/contracts", response_model=CustomerDetailOut, status_code=201)
async def add_contract(customer_id: int, body: ContractIn, _: User = Editor, db: AsyncSession = DB):
    return _detail(await svc.add_contract(db, customer_id, body))


@router.post("/{customer_id}/location/confirm", response_model=CustomerDetailOut)
async def confirm_location(customer_id: int, body: LocationConfirmIn, _: User = Confirmer, db: AsyncSession = DB):
    return _detail(await svc.confirm_location(db, customer_id, body))
