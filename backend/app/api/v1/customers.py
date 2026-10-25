"""Korxonalar bazasi. Har amal ruxsat kodi bilan (customers.*), admin bo'lmaganlar faqat o'z tumanlari doirasida."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_perm
from app.core.errors import not_found
from app.models import User
from app.models.enums import LocationStatus
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
from app.services import access
from app.services import customer_service as svc

router = APIRouter(prefix="/customers", tags=["customers"])
Reader = Depends(require_perm("customers.view"))
Creator = Depends(require_perm("customers.create"))
Editor = Depends(require_perm("customers.edit"))
Contracts = Depends(require_perm("customers.contract"))
Confirmer = Depends(require_perm("customers.location_confirm"))


def _detail(c) -> CustomerDetailOut:
    out = CustomerDetailOut.model_validate(c)
    out.contacts_count = len(c.contacts)
    return out


@router.get("", response_model=CustomerPage)
async def search(district_id: int | None = None, q: str | None = Query(None, max_length=100), incomplete: bool = False,
                 location: LocationStatus | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                 user: User = Reader, db: AsyncSession = DB):
    rows, total, counts = await repo.search(db, district_id=district_id, q=q, incomplete=incomplete, location=location,
                                            limit=limit, offset=offset, scope=access.scope(user))
    items = []
    for c in rows:
        item = CustomerListOut.model_validate(c)
        item.contacts_count = counts.get(c.id, 0)
        items.append(item)
    return CustomerPage(items=items, total=total)


@router.post("", response_model=CustomerDetailOut, status_code=201)
async def create(body: CustomerIn, user: User = Creator, db: AsyncSession = DB):
    return _detail(await svc.create(db, body, user))


@router.get("/{customer_id}", response_model=CustomerDetailOut)
async def detail(customer_id: int, user: User = Reader, db: AsyncSession = DB):
    cust = await repo.get(db, customer_id)
    if not cust:
        raise not_found("customer")
    svc.check_district_access(user, cust.district_id)
    return _detail(cust)


@router.patch("/{customer_id}", response_model=CustomerDetailOut)
async def update(customer_id: int, body: CustomerUpdateIn, user: User = Editor, db: AsyncSession = DB):
    return _detail(await svc.update(db, customer_id, body, user))


@router.post("/{customer_id}/contacts", response_model=CustomerDetailOut, status_code=201)
async def add_contact(customer_id: int, body: ContactIn, user: User = Editor, db: AsyncSession = DB):
    return _detail(await svc.add_contact(db, customer_id, body, user))


@router.post("/{customer_id}/contracts", response_model=CustomerDetailOut, status_code=201)
async def add_contract(customer_id: int, body: ContractIn, user: User = Contracts, db: AsyncSession = DB):
    return _detail(await svc.add_contract(db, customer_id, body, user))


@router.post("/{customer_id}/location/confirm", response_model=CustomerDetailOut)
async def confirm_location(customer_id: int, body: LocationConfirmIn, user: User = Confirmer, db: AsyncSession = DB):
    return _detail(await svc.confirm_location(db, customer_id, body, user))
