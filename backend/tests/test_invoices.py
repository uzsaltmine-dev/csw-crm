"""PR #16: buxgalteriya «Buyurtma varaqalari» va oylik schyot-faktura (yaratish, qayta yaratish, jo'natish, PDF, ochiq havola)."""
import asyncio
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import update

from app.models import Contract, Customer, OrderForm, Request
from app.models.enums import ContractType
from app.services import sms
from app.services.invoice_pdf import words_uz
from app.services.invoices import vat_of
from tests.test_accounting import _setup

T = date.today()
M = (T - timedelta(days=10)).replace(day=1)  # r2 (3 m³) shu oyda yashil bo'lgan


async def test_order_forms_and_invoice_by_volume(world, client_factory, sessionmaker):
    cid = await _setup(world, sessionmaker)  # kub, 50 000 so'm/m³
    async with sessionmaker() as s:
        await s.execute(update(Customer).where(Customer.id == cid).values(phone="+998 90 111-22-33"))
        await s.commit()
    acc, legal, gps = await client_factory("buxgalter"), await client_factory("legal"), await client_factory("gps")
    m = {"month": str(M)}
    f = (await legal.get("/api/v1/accounting/order-forms", params=m)).json()
    mine = [x for x in f["items"] if x["customer_id"] == cid]
    assert len(mine) >= 1 and all(x["contract_type"] == "by_volume" for x in mine)
    assert sum(x["amount"] for x in mine) == next(c for c in f["customers"] if c["customer_id"] == cid)["total"]
    assert (await gps.get("/api/v1/accounting/order-forms", params=m)).status_code == 403
    # Yaratish: faqat buxgalter (legal — faqat ko'radi)
    assert (await legal.post("/api/v1/accounting/invoices/generate", params=m)).status_code == 403
    g = (await acc.post("/api/v1/accounting/invoices/generate", params=m)).json()
    assert g["created"] == 1
    inv = (await acc.get("/api/v1/accounting/invoices", params=m)).json()["items"][0]
    total = sum(Decimal(str(x["amount"])) for x in mine)
    assert inv["status"] == "draft" and inv["number"] == f"SF-{M.year}-{M.month:02d}-00001"
    assert Decimal(str(inv["total"])) == total and Decimal(str(inv["vat"])) == vat_of(total)
    full = (await acc.get(f"/api/v1/accounting/invoices/{inv['id']}")).json()
    assert all(x["unit"] == "m³" and x["price"] == 50_000 for x in full["lines"])
    pdf = await acc.get(f"/api/v1/accounting/invoices/{inv['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    # Qayta yaratish: draft yangilanadi (raqam o'zgarmaydi), yangi faktura yaratilmaydi
    g = (await acc.post("/api/v1/accounting/invoices/generate", params=m)).json()
    assert g["created"] == 0 and g["updated"] == 1
    assert (await acc.get("/api/v1/accounting/invoices", params=m)).json()["items"][0]["number"] == inv["number"]
    # Jo'natilmagan fakturaning ochiq havolasi ishlamaydi
    async with sessionmaker() as s:
        from app.models import Invoice
        token = (await s.get(Invoice, inv["id"])).token
    anon = await client_factory(None)
    assert (await anon.get(f"/api/v1/public/invoices/{token}")).status_code == 404
    # Hammasiga jo'natish → SMS (summa + havola), status sent
    sms.SENT.clear()
    r = (await acc.post("/api/v1/accounting/invoices/send", params=m)).json()
    assert r["sent"] == 1
    await asyncio.sleep(0.05)
    assert sms.SENT and sms.SENT[-1][0] == "+998 90 111-22-33" and inv["number"] in sms.SENT[-1][1] and token in sms.SENT[-1][1]
    pub = await anon.get(f"/api/v1/public/invoices/{token}")
    assert pub.status_code == 200 and pub.content[:4] == b"%PDF"
    assert (await anon.get("/api/v1/public/invoices/xxx")).status_code == 404
    # Yuborilgan faktura qulf: qayta yaratish unga tegmaydi, qayta jo'natish ham yo'q
    g = (await acc.post("/api/v1/accounting/invoices/generate", params=m)).json()
    assert g["skipped_sent"] == 1 and g["updated"] == 0
    assert (await acc.post("/api/v1/accounting/invoices/send", params=m)).json()["total"] == 0


async def test_monthly_contract_one_line_plus_annex(world, client_factory, sessionmaker):
    cid = await _setup(world, sessionmaker, ctype=ContractType.monthly, price=300_000)
    acc = await client_factory("buxgalter")
    m = {"month": str(M)}
    f = (await acc.get("/api/v1/accounting/order-forms", params=m)).json()
    assert all(x["amount"] == 0 for x in f["items"] if x["customer_id"] == cid)
    await acc.post("/api/v1/accounting/invoices/generate", params=m)
    inv = next(i for i in (await acc.get("/api/v1/accounting/invoices", params=m)).json()["items"] if i["customer_id"] == cid)
    lines = (await acc.get(f"/api/v1/accounting/invoices/{inv['id']}")).json()["lines"]
    assert [x["kind"] for x in lines if x["kind"] != "annex"] == ["monthly"] and inv["total"] == 300_000
    assert any(x["kind"] == "annex" and x["amount"] == 0 for x in lines)
    assert (await acc.get(f"/api/v1/accounting/invoices/{inv['id']}/pdf")).content[:4] == b"%PDF"


async def test_per_trip_and_scope(world, client_factory, sessionmaker):
    cid = await _setup(world, sessionmaker, ctype=ContractType.per_trip, price=120_000)
    acc, gps = await client_factory("buxgalter"), await client_factory("gps")
    m = {"month": str(M)}
    await acc.post("/api/v1/accounting/invoices/generate", params=m)
    inv = (await acc.get("/api/v1/accounting/invoices", params=m)).json()["items"][0]
    lines = (await acc.get(f"/api/v1/accounting/invoices/{inv['id']}")).json()["lines"]
    assert lines and all(x["unit"] == "reys" and x["amount"] == 120_000 for x in lines)
    assert (await gps.get(f"/api/v1/accounting/invoices/{inv['id']}/pdf")).status_code == 403


async def test_provider_requisites(world, client_factory):
    admin, manager = await client_factory("admin"), await client_factory("manager")
    provs = (await manager.get("/api/v1/admin/providers")).json()
    if not provs:
        return
    pid = provs[0]["id"]
    body = {"full_name": "Test MChJ", "inn": "301234567", "mfo": "00873", "account": "20208000900123456001", "director": "A. Aliyev"}
    assert (await manager.put(f"/api/v1/admin/providers/{pid}", json=body)).status_code == 403
    r = await admin.put(f"/api/v1/admin/providers/{pid}", json=body)
    assert r.status_code == 200 and r.json()["inn"] == "301234567"
    assert (await admin.put(f"/api/v1/admin/providers/{pid}", json={**body, "inn": "12"})).status_code == 422


def test_words_uz():
    assert words_uz(1_250_000) == "bir million ikki yuz ellik ming"
    assert words_uz(16_071) == "o'n olti ming yetmish bir"
    assert words_uz(0) == "nol"
