"""Debitor/kreditor hisobi (vaqtincha tizim ichida; o'z buxgalteriya tizimimiz tayyor bo'lgach shu modul uning API'siga almashtiriladi).

Hisoblangan summa (xizmat) shartnoma turiga qarab:
  per_trip  — narx × yashil murojaatlar soni;   by_volume — narx × kub;
  monthly   — shartnoma amal qilgan har oy uchun narx (oyning 1-kuni, yoki shartnoma boshlangan kun);
  one_off   — narx bir marta (shartnoma boshlangan kun).
Qoldiq = hisoblangan − to'langan. Musbat — debitor (korxona qarzdor), manfiy — kreditor (oldindan to'lagan).
"""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Act, Contract, Customer, OrderForm, Payment, Request, User
from app.models.enums import ContractType, RequestStatus
from app.services import access

TASHKENT = timezone(timedelta(hours=5))
GREEN = (RequestStatus.done, RequestStatus.suspect)
ZERO = Decimal("0")


def local_day(dt: datetime) -> date:
    return dt.replace(tzinfo=timezone.utc).astimezone(TASHKENT).date()


def money(v) -> Decimal:
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))


@dataclass
class Entry:
    day: date
    amount: Decimal
    kind: str  # "charge" | "payment"


@dataclass
class Green:
    request: Request
    day: date
    volume: Decimal
    closed_via: str | None
    contract: Contract | None
    amount: Decimal


def _months(start: date, end: date):
    d = start.replace(day=1)
    while d <= end:
        yield d
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)


def contract_for(contracts: list[Contract], req: Request, day: date) -> Contract | None:
    if req.contract_id:
        c = next((c for c in contracts if c.id == req.contract_id), None)
        if c:
            return c
    return next((c for c in reversed(contracts) if c.valid_from <= day <= c.valid_to), None)


class Ledger:
    """Bir nechta korxona uchun hisob-kitob ma'lumotlari (bazadan bir martada yuklanadi)."""

    def __init__(self, customers: list[Customer], contracts, greens, volumes, payments, today: date):
        self.customers = {c.id: c for c in customers}
        self.contracts: dict[int, list[Contract]] = defaultdict(list)
        for c in contracts:
            self.contracts[c.customer_id].append(c)
        self.greens: dict[int, list[Green]] = defaultdict(list)
        self.entries: dict[int, list[Entry]] = defaultdict(list)
        self.today = today
        for r in greens:
            day = local_day(r.finished_at or r.created_at)
            vol, via = volumes.get(r.id, (ZERO, None))
            ct = contract_for(self.contracts[r.customer_id], r, day)
            amount = ZERO
            if ct and ct.price is not None:
                if ct.type == ContractType.per_trip:
                    amount = money(ct.price)
                elif ct.type == ContractType.by_volume:
                    amount = money(Decimal(str(ct.price)) * vol)
            self.greens[r.customer_id].append(Green(r, day, vol, via, ct, amount))
            if amount:
                self.entries[r.customer_id].append(Entry(day, amount, "charge"))
        for cid, cts in self.contracts.items():
            for ct in cts:
                if ct.price is None or not ct.is_active:
                    continue
                if ct.type == ContractType.monthly:
                    for m in _months(ct.valid_from, min(ct.valid_to, today)):
                        self.entries[cid].append(Entry(max(m, ct.valid_from), money(ct.price), "charge"))
                elif ct.type == ContractType.one_off and ct.valid_from <= today:
                    self.entries[cid].append(Entry(ct.valid_from, money(ct.price), "charge"))
        for p in payments:
            self.entries[p.customer_id].append(Entry(p.paid_on, money(p.amount), "payment"))

    def totals(self, cid: int, start: date | None, end: date) -> tuple[Decimal, Decimal]:
        charged = paid = ZERO
        for e in self.entries[cid]:
            if (start is None or e.day >= start) and e.day <= end:
                if e.kind == "charge":
                    charged += e.amount
                else:
                    paid += e.amount
        return charged, paid

    def balance(self, cid: int, at: date) -> Decimal:
        c, p = self.totals(cid, None, at)
        return c - p

    def row(self, cid: int) -> dict:
        bal = self.balance(cid, self.today)
        c = self.customers[cid]
        return {"customer_id": cid, "name": c.name, "code": c.code, "district_id": c.district_id,
                "debit": float(max(bal, ZERO)), "credit": float(max(-bal, ZERO)), "balance": float(bal),
                "volume_m3": float(sum((g.volume for g in self.greens[cid]), ZERO)), "green_count": len(self.greens[cid])}


async def load(db: AsyncSession, customers: list[Customer]) -> Ledger:
    ids = [c.id for c in customers] or [-1]
    contracts = list((await db.execute(select(Contract).where(Contract.customer_id.in_(ids)).order_by(Contract.valid_from, Contract.id))).scalars())
    greens = list((await db.execute(select(Request).where(Request.customer_id.in_(ids), Request.status.in_(GREEN))
                                    .options(selectinload(Request.vehicle), selectinload(Request.driver))
                                    .order_by(Request.finished_at))).scalars())
    gids = [r.id for r in greens] or [-1]
    volumes: dict[int, tuple[Decimal, str | None]] = {}
    for rid, vol in (await db.execute(select(Act.request_id, Act.volume_m3).where(Act.request_id.in_(gids)))).all():
        volumes[rid] = (Decimal(str(vol or 0)), "act")
    for rid, vol, via in (await db.execute(select(OrderForm.request_id, OrderForm.volume_m3, OrderForm.closed_via)
                                           .where(OrderForm.request_id.in_(gids), OrderForm.closed_at.is_not(None)))).all():
        if vol is not None and rid not in volumes:
            volumes[rid] = (Decimal(str(vol)), via or "form")
    payments = list((await db.execute(select(Payment).where(Payment.customer_id.in_(ids), Payment.cancelled_at.is_(None)))).scalars())
    return Ledger(customers, contracts, greens, volumes, payments, local_day(datetime.now(timezone.utc).replace(tzinfo=None)))


async def scoped_customers(db: AsyncSession, actor: User, only_contracted: bool = True, customer_id: int | None = None) -> list[Customer]:
    q = select(Customer)
    s = access.scope(actor)
    if s is not None:
        q = q.where(Customer.district_id.in_(s or {-1}))
    if customer_id is not None:
        q = q.where(Customer.id == customer_id)
    if only_contracted:
        q = q.where(Customer.id.in_(select(Contract.customer_id)))
    return list((await db.execute(q.order_by(Customer.name))).scalars())


async def companies(db: AsyncSession, actor: User, q: str | None = None) -> dict:
    custs = await scoped_customers(db, actor)
    ledger = await load(db, custs)
    today = ledger.today
    contracted = [c for c in custs if any(ct.valid_from <= today <= ct.valid_to and ct.is_active for ct in ledger.contracts[c.id])]
    rows = [ledger.row(c.id) for c in custs]
    if q and q.strip():
        t = q.strip().lower()
        rows = [r for r in rows if t in r["name"].lower() or t == (r["code"] or "").lower()]
    return {"total_contracted": len(contracted), "total": len(custs), "items": rows,
            "sum": {"debit": sum(r["debit"] for r in rows), "credit": sum(r["credit"] for r in rows),
                    "volume_m3": sum(r["volume_m3"] for r in rows)}}


async def _one(db: AsyncSession, actor: User, customer_id: int) -> tuple[Customer, Ledger]:
    from app.core.errors import not_found
    custs = await scoped_customers(db, actor, only_contracted=False, customer_id=customer_id)
    if not custs:
        raise not_found("customer")
    return custs[0], await load(db, custs)


async def compare(db: AsyncSession, actor: User, customer_id: int, periods: list[tuple[date, date]]) -> dict:
    """Ikki (yoki bir nechta) davr: davr boshidagi va oxiridagi qoldiq, hisoblangan, to'langan; oyma-oy aylanma."""
    from app.core.errors import invalid
    for a, b in periods:
        if b < a:
            raise invalid("bad_dates", "Davr oxiri boshidan oldin bo'lmasin")
    cust, led = await _one(db, actor, customer_id)
    out = []
    for a, b in periods:
        opening = led.balance(cust.id, a - timedelta(days=1))
        charged, paid = led.totals(cust.id, a, b)
        closing = opening + charged - paid
        out.append({"from": a, "to": b, "opening": float(opening), "charged": float(charged), "paid": float(paid),
                    "closing": float(closing), "debit": float(max(closing, ZERO)), "credit": float(max(-closing, ZERO))})
    start, end = min(a for a, _ in periods), max(b for _, b in periods)
    months = []
    for m in _months(start, end):
        nxt = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
        c, p = led.totals(cust.id, max(m, start), min(nxt - timedelta(days=1), end))
        months.append({"month": m.strftime("%Y-%m"), "charged": float(c), "paid": float(p),
                       "closing": float(led.balance(cust.id, min(nxt - timedelta(days=1), end)))})
    return {"customer": {"id": cust.id, "name": cust.name, "code": cust.code, "stir": cust.stir}, "periods": out, "months": months,
            "now": led.row(cust.id)}


async def green_list(db: AsyncSession, actor: User, customer_id: int) -> dict:
    cust, led = await _one(db, actor, customer_id)
    items = [{"id": g.request.id, "number": g.request.number, "day": g.day, "volume_m3": float(g.volume),
              "waste_type": g.request.waste_type.value, "plate": g.request.vehicle.plate if g.request.vehicle else None,
              "driver_name": g.request.driver.full_name if g.request.driver else None, "closed_via": g.closed_via,
              "status": g.request.status.value, "contract": g.contract.number if g.contract else None, "amount": float(g.amount)}
             for g in sorted(led.greens[cust.id], key=lambda g: (g.day, g.request.id), reverse=True)]
    return {"customer": {"id": cust.id, "name": cust.name, "code": cust.code, "stir": cust.stir}, "items": items,
            "total_m3": float(sum((g.volume for g in led.greens[cust.id]), ZERO)), "count": len(items)}
