"""PR #13: operatorning yangi korxonasi (maxsus raqam + SMS), STIR xatosi, shartnomasiz murojaat GPS'ga ko'rinmaydi,
qora bosqich, 12/72/144 soatlik hisoblar, M- raqamlar, GPS socket xonasi."""
import asyncio
from datetime import date, timedelta

from sqlalchemy import select, update

from app.db.base import utcnow
from app.models import Customer, CustomerContact, Request
from app.services import sms


async def test_new_company_gets_code_and_sms(world, client_factory, sessionmaker):
    op, legal, gps = await client_factory("operator"), await client_factory("legal"), await client_factory("gps")
    a = world["districts"]["a"]
    sms.SENT.clear()
    body = {"phone": "94 512 11 16", "stir": "309876543", "contact_name": "Karimov Anvar"}
    r = await op.post("/api/v1/appeals/new-company", json=body)
    assert r.json()["error"]["code"] == "district_required"  # operatorda 2 ta tuman
    r = await op.post("/api/v1/appeals/new-company", json={**body, "district_id": a})
    assert r.status_code == 201, r.text
    ap = r.json()
    assert ap["number"].startswith("MR-") and ap["caller_name"] == "Karimov Anvar" and ap["customer_id"]
    await asyncio.sleep(0.05)  # SMS fon vazifasi
    async with sessionmaker() as s:
        cust = await s.get(Customer, ap["customer_id"])
        contact = (await s.execute(select(CustomerContact).where(CustomerContact.customer_id == cust.id))).scalar_one()
    assert cust.stir == "309876543" and contact.name == "Karimov Anvar" and cust.phone == "+998 94 512-11-16"
    assert sms.SENT and sms.SENT[-1][0] == "+998 94 512-11-16" and cust.code in sms.SENT[-1][1] and "hech kimga" in sms.SENT[-1][1]
    assert cust.code not in r.text  # operatorga maxsus raqam qaytarilmaydi
    # Shu STIR bilan yana — xato va mavjud korxona
    r = await op.post("/api/v1/appeals/new-company", json={**body, "district_id": a})
    err = r.json()["error"]
    assert r.status_code == 409 and err["code"] == "stir_taken" and err["details"]["customer_id"] == cust.id
    # Legal qabul qiladi: o'sha karta to'ldiriladi (yangisi ochilmaydi), shartnoma bilan
    accept = {"customer": {"name": "Navbahor Savdo MChJ", "district_id": a, "stir": "309876543", "address": "Navoiy 7"},
              "contract": {"number": "SH-2026/0901", "type": "per_trip", "valid_from": str(date.today()),
                           "valid_to": str(date.today() + timedelta(days=200))}}
    r = await legal.post(f"/api/v1/appeals/{ap['id']}/accept", json=accept)
    assert r.status_code == 200, r.text
    assert r.json()["customer_id"] == cust.id
    async with sessionmaker() as s:
        c2 = await s.get(Customer, cust.id)
        assert c2.name == "Navbahor Savdo MChJ" and c2.code == cust.code
        assert (await s.execute(select(Customer).where(Customer.stir == "309876543"))).scalars().all() == [c2]
    # Shartnoma bor — GPS ko'radi
    assert any(x["customer"]["id"] == cust.id for x in (await gps.get("/api/v1/gps/requests")).json())


async def test_gps_hides_requests_without_contract(world, client_factory, sessionmaker):
    gps = await client_factory("gps")
    async with sessionmaker() as s:
        c = Customer(fixed_no="A-0900", name="Shartnomasiz", name_key="shartnomasiz", district_id=world["districts"]["a"])
        s.add(c); await s.flush()
        r = Request(customer_id=c.id, district_id=world["districts"]["a"]); s.add(r); await s.flush(); r.number = f"M-{r.id:06d}"
        await s.commit()
        hidden = r.id
    ids = [x["id"] for x in (await gps.get("/api/v1/gps/requests")).json()]
    assert hidden not in ids and set(world["requests"]) <= set(ids)


async def test_black_stage_and_summary(world, client_factory, sessionmaker):
    admin, gps = await client_factory("admin"), await client_factory("gps")
    r1, r2, r3 = world["requests"]
    async with sessionmaker() as s:
        await s.execute(update(Request).where(Request.id == r1).values(created_at=utcnow() - timedelta(hours=80)))
        await s.execute(update(Request).where(Request.id == r2).values(created_at=utcnow() - timedelta(hours=20)))
        await s.commit()
    items = {x["id"]: x["stage"] for x in (await admin.get("/api/v1/requests")).json()["items"]}
    assert items == {r1: "black", r2: "red", r3: "red"}
    assert [x["id"] for x in (await admin.get("/api/v1/requests", params={"stage": "black"})).json()["items"]] == [r1]
    s12 = (await admin.get("/api/v1/requests-summary", params={"hours": 12})).json()
    s72 = (await admin.get("/api/v1/requests-summary", params={"hours": 72})).json()
    s144 = (await admin.get("/api/v1/requests-summary", params={"hours": 144})).json()
    assert (s12["red"], s12["black"]) == (1, 0) and (s72["red"], s72["black"]) == (2, 0) and (s144["red"], s144["black"]) == (2, 1)
    assert s144["yellow"] == 0 and s144["green"] == 0
    # GPS kartasi ham qora ekanini biladi
    assert next(x for x in (await gps.get("/api/v1/gps/requests")).json() if x["id"] == r1)["stage"] == "black"


async def test_gps_socket_room_from_user(world, sessionmaker, monkeypatch):
    from app import realtime
    from app.core.security import ACCESS, create_token
    import app.db.session as session_mod
    monkeypatch.setattr(session_mod, "SessionLocal", sessionmaker)
    rooms: list[str] = []

    async def enter(sid, room):
        rooms.append(room)
    monkeypatch.setattr(realtime.sio, "enter_room", enter)
    token = create_token(world["users"]["gps"], "gps", ACCESS)
    assert await realtime.connect("sid1", {}, {"token": token}) is True
    assert f"gps:{world['districts']['a']}" in rooms
