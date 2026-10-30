"""Call-center: ariza ochish va takroriy ariza, bekor qilish, birinchi murojaat → yurist, 72 soat, statistika."""
from datetime import date, timedelta

from sqlalchemy import select, update

from app.db.base import utcnow
from app.models import Customer, Request, SituationEvent
from app.models.enums import RequestStatus
from app.services.callcenter import check_overdue
from tests.test_permissions import _manager_a

ORDER = {"waste_type": "septic", "volume_estimate": 4, "preferred_time": "09:00–12:00", "note": "Chuqur to'lgan",
         "caller_name": "Aliyev Vali", "caller_phone": "94 512 11 16"}


async def test_operator_request_and_repeat_confirmation(world, client_factory):
    op, gps = await client_factory("operator"), await client_factory("gps")
    cid = world["customer"].id
    opened = (await op.get("/api/v1/requests/open", params={"customer_id": cid})).json()
    assert len(opened) == 3  # world: 3 ta yangi ariza
    r = await op.post("/api/v1/requests", json={"customer_id": cid, **ORDER})
    assert r.status_code == 409 and r.json()["error"]["code"] == "open_request_exists"
    r = await op.post("/api/v1/requests", json={"customer_id": cid, **ORDER, "confirm_repeat": True})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["is_repeat"] and b["repeat_of_id"] == opened[0]["id"] and b["number"] == f"M-{b['id']:06d}"
    assert b["caller_phone"] == "+998 94 512-11-16" and b["waste_type"] == "septic" and b["source"] == "phone"
    assert b["contract"]["number"] == "SH-2026/0001" and b["status"] == "new" and not b["overdue"]
    # GPS xodimi ro'yxatida darhol, "qayta" belgisi bilan
    listed = next(x for x in (await gps.get("/api/v1/gps/requests")).json() if x["id"] == b["id"])
    assert listed["is_repeat"] is True and listed["due_at"]
    mine = (await op.get("/api/v1/requests", params={"mine": "true"})).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == b["id"]


async def test_request_deadline_is_72_hours(world, client_factory, sessionmaker):
    op = await client_factory("operator")
    b = (await op.post("/api/v1/requests", json={"customer_id": world["customer"].id, **ORDER, "confirm_repeat": True})).json()
    async with sessionmaker() as s:
        req = await s.get(Request, b["id"])
        assert abs((req.due_at - req.created_at) - timedelta(hours=72)) < timedelta(seconds=5)


async def test_cancel_rules(world, client_factory):
    op, admin = await client_factory("operator"), await client_factory("admin")
    rid = world["requests"][0]
    assert (await op.post(f"/api/v1/requests/{rid}/cancel", json={"reason": "Mijoz voz kechdi"})).status_code == 403
    r = await admin.post(f"/api/v1/requests/{rid}/cancel", json={"reason": "Mijoz voz kechdi"})
    assert r.status_code == 200 and r.json()["status"] == "cancelled" and r.json()["cancel_reason"] == "Mijoz voz kechdi"
    assert (await admin.post(f"/api/v1/requests/{rid}/cancel", json={"reason": "yana"})).json()["error"]["code"] == "request_not_new"


async def test_first_appeal_goes_to_legal_and_becomes_request(world, client_factory, sessionmaker):
    op, legal, gps = await client_factory("operator"), await client_factory("legal"), await client_factory("gps")
    a = world["districts"]["a"]
    body = {"district_id": a, "org_name": "Yangi Bozor MChJ", "address": "Navoiy 5", "activity_type": "Savdo",
            "caller_name": "Karimov", "caller_phone": "+998901112233", **{k: ORDER[k] for k in ("waste_type", "volume_estimate", "note")}}
    r = await op.post("/api/v1/appeals", json=body)
    assert r.status_code == 201 and r.json()["number"].startswith("MR-") and r.json()["status"] == "new"
    aid = r.json()["id"]
    queue = (await legal.get("/api/v1/appeals", params={"status": "new"})).json()
    assert [x["id"] for x in queue] == [aid]
    accept = {"customer": {"name": "Yangi Bozor MChJ", "district_id": a, "stir": "301222333", "address": "Navoiy 5", "phone": "901112233"},
              "contract": {"number": "SH-2026/0777", "type": "per_trip", "valid_from": str(date.today()),
                           "valid_to": str(date.today() + timedelta(days=90))}}
    # Shartnoma raqami band bo'lsa — korxona ham yaratilmaydi
    bad = {**accept, "contract": {**accept["contract"], "number": "SH-2026/0001"}}
    assert (await legal.post(f"/api/v1/appeals/{aid}/accept", json=bad)).json()["error"]["code"] == "contract_number_taken"
    async with sessionmaker() as s:
        assert (await s.execute(select(Customer).where(Customer.stir == "301222333"))).first() is None
    r = await legal.post(f"/api/v1/appeals/{aid}/accept", json=accept)
    assert r.status_code == 200, r.text
    ap = r.json()
    assert ap["status"] == "accepted" and ap["customer_id"] and ap["request_id"]
    req = next(x for x in (await gps.get("/api/v1/gps/requests")).json() if x["id"] == ap["request_id"])
    assert req["customer"]["stir"] == "301222333" and req["customer"]["missing_fields"] == [] and req["waste_type"] == "septic"
    assert req["is_repeat"] is False
    assert (await legal.post(f"/api/v1/appeals/{aid}/accept", json=accept)).json()["error"]["code"] == "appeal_not_new"
    # Rad etish
    aid2 = (await op.post("/api/v1/appeals", json={**body, "org_name": "Boshqa MChJ"})).json()["id"]
    r = await legal.post(f"/api/v1/appeals/{aid2}/reject", json={"reason": "Jismoniy shaxs — xizmat ko'rsatilmaydi"})
    assert r.json()["status"] == "rejected"
    mine = (await op.get("/api/v1/appeals", params={"mine": "true"})).json()
    assert {x["status"] for x in mine} == {"accepted", "rejected"}
    assert (await op.post(f"/api/v1/appeals/{aid2}/accept", json=accept)).status_code == 403  # operator ko'rib chiqa olmaydi


async def test_overdue_requests_reported_once(world, client_factory, sessionmaker):
    admin = await client_factory("admin")
    rid = world["requests"][1]
    async with sessionmaker() as s:
        await s.execute(update(Request).where(Request.id == rid).values(due_at=utcnow() - timedelta(hours=1)))
        await s.commit()
        assert await check_overdue(s) == 1
        assert await check_overdue(s) == 0
        ev = (await s.execute(select(SituationEvent).where(SituationEvent.kind == "request_overdue"))).scalar_one()
        assert ev.ref_id == rid and ev.level.value == "warning"
    page = (await admin.get("/api/v1/requests", params={"overdue": "true"})).json()
    assert page["total"] == 1 and page["items"][0]["overdue"] is True


async def test_stats_by_period_and_scope(world, client_factory, sessionmaker):
    admin = await client_factory("admin")
    r1, r2, r3 = world["requests"]
    async with sessionmaker() as s:
        await s.execute(update(Request).where(Request.id == r1).values(status=RequestStatus.done))
        await s.execute(update(Request).where(Request.id == r2).values(due_at=utcnow() - timedelta(hours=1)))
        await s.execute(update(Request).where(Request.id == r3).values(is_repeat=True))
        await s.commit()
    st = (await admin.get("/api/v1/stats/summary", params={"period": "today"})).json()
    assert st["total"] == {"received": 3, "repeat": 1, "pending": 1, "overdue": 1, "done": 1, "not_done": 2,
                           "done_share": 33.3, "not_done_share": 66.7}
    by = {d["name"]: d for d in st["districts"]}
    assert by["Asaka tumani"]["received"] == 3 and by["Termiz shahri"]["received"] == 0
    for p in ("month", "last10", "last5"):
        assert (await admin.get("/api/v1/stats/summary", params={"period": p})).json()["total"]["received"] == 3
    assert (await admin.get("/api/v1/stats/summary", params={"period": "year"})).status_code == 422
    # Manager — faqat o'z tumani; operator/haydovchida statistika yo'q
    _, mgr = await _manager_a(world, client_factory, admin, [])
    st = (await mgr.get("/api/v1/stats/summary")).json()
    assert [d["name"] for d in st["districts"]] == ["Asaka tumani"]
    for u in ("operator", "driver"):
        assert (await (await client_factory(u)).get("/api/v1/stats/summary")).status_code == 403


async def test_requests_scope_and_permissions(world, client_factory):
    driver = await client_factory("driver")
    assert (await driver.get("/api/v1/requests")).status_code == 403
    gps_a = await client_factory("gps")
    assert (await gps_a.get("/api/v1/requests")).json()["total"] == 3
    admin = await client_factory("admin")
    _, mgr = await _manager_a(world, client_factory, admin, [])
    assert (await mgr.post("/api/v1/requests", json={"customer_id": world["customer"].id})).status_code == 403  # requests.create yo'q
