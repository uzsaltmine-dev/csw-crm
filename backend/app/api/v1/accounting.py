"""Buxgalteriya (vaqtincha tizim ichida): korxonalar debitor/kreditori, davrlarni solishtirish, yashil murojaatlar, to'lovlar."""
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_perm
from app.models import User
from app.services import billing, payments

router = APIRouter(prefix="/accounting", tags=["accounting"])
View = Depends(require_perm("accounting.view"))
Pay = Depends(require_perm("accounting.payments"))


@router.get("/companies")
async def companies(q: str | None = Query(None, max_length=100), district_id: int | None = None, user: User = View,
                    db: AsyncSession = DB) -> dict:
    """Shartnomasi bor korxonalar: debitor, kreditor, jami kub (legal «Korxonalar» jadvali)."""
    return await billing.companies(db, user, q, district_id)


@router.get("/new-contracts")
async def new_contracts(district_id: int | None = None, user: User = View, db: AsyncSession = DB) -> dict:
    """Yangi shartnomalar: 7 kun, 15 kun, 1 oy, 6 oy, 1 yil — jami va tumanlar kesimida."""
    return await billing.new_contracts(db, user, district_id)


@router.get("/companies/{customer_id}/compare")
async def compare(customer_id: int, a_from: date, a_to: date, b_from: date, b_to: date, user: User = View, db: AsyncSession = DB) -> dict:
    return await billing.compare(db, user, customer_id, [(a_from, a_to), (b_from, b_to)])


@router.get("/companies/{customer_id}/green")
async def green(customer_id: int, user: User = View, db: AsyncSession = DB) -> dict:
    """Korxonaga xizmat ko'rsatilgan barcha yashil murojaatlar — har birining kubi bilan."""
    return await billing.green_list(db, user, customer_id)


class PaymentIn(BaseModel):
    customer_id: int
    paid_on: date
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    doc_no: str | None = Field(None, max_length=50)
    note: str | None = Field(None, max_length=255)


class CancelIn(BaseModel):
    reason: str = Field(min_length=3, max_length=255)


@router.get("/payments")
async def list_payments(q: str | None = Query(None, max_length=100), date_from: date | None = None, date_to: date | None = None,
                        customer_id: int | None = None, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0),
                        user: User = View, db: AsyncSession = DB) -> dict:
    rows, total, s = await payments.search(db, user, q, date_from, date_to, customer_id, limit, offset)
    return {"items": [payments.out(p) for p in rows], "total": total, "sum": s}


@router.post("/payments", status_code=201)
async def create_payment(body: PaymentIn, user: User = Pay, db: AsyncSession = DB) -> dict:
    return payments.out(await payments.create(db, user, body.customer_id, body.paid_on, body.amount, body.doc_no, body.note))


@router.post("/payments/{payment_id}/cancel")
async def cancel_payment(payment_id: int, body: CancelIn, user: User = Pay, db: AsyncSession = DB) -> dict:
    return payments.out(await payments.cancel(db, user, payment_id, body.reason))


@router.post("/payments/import")
async def import_payments(dry_run: bool = True, file: UploadFile = File(...), user: User = Pay, db: AsyncSession = DB) -> dict:
    """Bank ko'chirmasi (xlsx/xls/csv): maxsus raqam yoki STIR, sana, summa, hujjat raqami. Avval dry_run=true."""
    return await payments.import_file(db, user, file.filename or "statement.xlsx", await file.read(), dry_run)
