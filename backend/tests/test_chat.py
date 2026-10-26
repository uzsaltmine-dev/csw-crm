"""PR #11: ariza va murojaat ichidagi yozishma — kirish huquqlari, faqat o'qish, ovoz, o'qilmaganlar, tozalash."""
from datetime import date, timedelta

from sqlalchemy import select, update

from app.db.base import utcnow
from app.models import ChatMessage, Customer, Request
from app.models.enums import RequestStatus
from app.services import chat as chat_svc
from app.services.storage import MemoryStorage
from tests.helpers import open_and_start_shift

WEBM = b"\x1aE\xdf\xa3" + b"\x00" * 2000


def url(rid: int, tail: str = "", kind: str = "request") -> str:
    return f"/api/v1/chat/{kind}/{rid}{tail}"


async def _request_in_b(world, sessionmaker) -> int:
    async with sessionmaker() as s:
        c = Customer(fixed_no="B-1", name="Termiz MChJ", name_key="termiz mchj", district_id=world["districts"]["b"])
        s.add(c); await s.flush()
        r = Request(customer_id=c.id, district_id=world["districts"]["b"])
        s.add(r); await s.flush(); r.number = f"AR-{r.id:06d}"
        await s.commit()
        return r.id


async def test_who_can_see_request_chat(world, client_factory, sessionmaker):
    op, gps, admin = await client_factory("operator"), await client_factory("gps"), await client_factory("admin")
    driver, driver2 = await client_factory("driver"), await client_factory("driver2")
    rid = world["requests"][0]
    r = await op.post(url(rid, "/text"), json={"text": "  Mijoz 14:00 dan keyin bo'ladi  "})
    assert r.status_code == 201 and r.json()["text"] == "Mijoz 14:00 dan keyin bo'ladi" and r.json()["author_role"] == "operator"
    assert (await gps.post(url(rid, "/text"), json={"text": "Tushunarli"})).status_code == 201
    d = (await admin.get(url(rid))).json()
    assert [m["author_name"] for m in d["items"]] == ["Operator", "GPS"] and d["can_write"] and not d["closed"]
    # Haydovchi: biriktirilgunga qadar ko'rmaydi, keyin faqat o'zi
    assert (await driver.get(url(rid))).status_code == 403
    await open_and_start_shift(gps, driver, world["users"]["driver"], world["vehicles"]["v1"])
    assert (await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})).status_code == 200
    assert len((await driver.get(url(rid))).json()["items"]) == 2
    assert (await driver.post(url(rid, "/text"), json={"text": "Yo'ldaman"})).status_code == 201
    assert (await driver2.get(url(rid))).status_code == 403
    # Boshqa tuman: GPS (A tumani) B tumanidagi arizani ko'rmaydi
    rb = await _request_in_b(world, sessionmaker)
    assert (await gps.get(url(rb))).status_code == 403
    assert (await admin.get(url(rb))).status_code == 200
    # Bo'sh yoki juda uzun xabar
    assert (await op.post(url(rid, "/text"), json={"text": "   "})).json()["error"]["code"] == "empty_message"
    assert (await op.post(url(rid, "/text"), json={"text": "x" * 2001})).status_code == 422


async def test_manager_scope_and_permission_toggle(world, client_factory):
    from tests.test_permissions import _manager_a
    admin = await client_factory("admin")
    rid = world["requests"][0]
    uid, mgr = await _manager_a(world, client_factory, admin, [])
    assert (await mgr.post(url(rid, "/text"), json={"text": "salom"})).status_code == 201  # andoza: ko'rish + yozish
    me = (await mgr.get("/api/v1/auth/me")).json()["permissions"]
    r = await admin.put(f"/api/v1/admin/users/{uid}/access", json={"permissions": [p for p in me if p != "chat.write"]})
    assert r.status_code == 200, r.text
    assert (await mgr.get(url(rid))).status_code == 200
    assert (await mgr.post(url(rid, "/text"), json={"text": "salom"})).status_code == 403


async def test_closed_request_is_read_only_except_manager(world, client_factory):
    op, admin, manager = await client_factory("operator"), await client_factory("admin"), await client_factory("manager")
    rid = world["requests"][0]
    await op.post(url(rid, "/text"), json={"text": "Bekor qilinsinmi?"})
    assert (await admin.post(f"/api/v1/requests/{rid}/cancel", json={"reason": "Mijoz voz kechdi"})).status_code == 200
    d = (await op.get(url(rid))).json()
    assert d["closed"] and not d["can_write"] and len(d["items"]) == 1
    r = await op.post(url(rid, "/text"), json={"text": "yana"})
    assert r.status_code == 403
    assert (await manager.post(url(rid, "/text"), json={"text": "Yopildi, rahmat"})).status_code == 201


async def test_appeal_chat_hidden_from_gps_and_carried_into_request(world, client_factory):
    op, legal, gps = await client_factory("operator"), await client_factory("legal"), await client_factory("gps")
    a = world["districts"]["a"]
    aid = (await op.post("/api/v1/appeals", json={"district_id": a, "org_name": "Yangi Bozor MChJ", "caller_phone": "+998901112233"})).json()["id"]
    assert (await op.post(url(aid, "/text", "appeal"), json={"text": "STIR keyin aytadi"})).status_code == 201
    assert (await legal.post(url(aid, "/text", "appeal"), json={"text": "Mayli, kutaman"})).status_code == 201
    assert (await gps.get(url(aid, kind="appeal"))).status_code == 403
    accept = {"customer": {"name": "Yangi Bozor MChJ", "district_id": a, "stir": "301222333", "address": "Navoiy 5"},
              "contract": {"number": "SH-2026/0777", "type": "per_trip", "valid_from": str(date.today()),
                           "valid_to": str(date.today() + timedelta(days=300)), "signed_on": str(date.today())}}
    rid = (await legal.post(f"/api/v1/appeals/{aid}/accept", json=accept)).json()["request_id"]
    # Murojaat yopildi — endi faqat o'qish; yozishma ariza ichida davom etadi
    assert (await op.post(url(aid, "/text", "appeal"), json={"text": "?"})).status_code == 403
    d = (await gps.get(url(rid))).json()
    assert [(m["thread_type"], m["text"]) for m in d["items"]] == [("appeal", "STIR keyin aytadi"), ("appeal", "Mayli, kutaman")]
    assert d["appeal_id"] == aid and d["can_write"]
    assert (await gps.post(url(rid, "/text"), json={"text": "Ertaga boramiz"})).status_code == 201


async def test_voice_message_limits_and_audio_access(world, client_factory, app):
    gps, op, driver2 = await client_factory("gps"), await client_factory("operator"), await client_factory("driver2")
    rid = world["requests"][0]
    send = lambda c, data=WEBM, ctype="audio/webm;codecs=opus", dur="12.4": c.post(  # noqa: E731
        url(rid, "/voice"), data={"duration": dur}, files={"audio": ("v.webm", data, ctype)})
    r = await send(gps)
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["kind"] == "voice" and m["duration_s"] == 12 and m["has_audio"]
    a = await op.get(f"/api/v1/chat/audio/{m['id']}")
    assert a.status_code == 200 and a.content == WEBM and a.headers["content-type"].startswith("audio/webm")
    assert (await driver2.get(f"/api/v1/chat/audio/{m['id']}")).status_code == 403
    assert (await send(gps, dur="75")).json()["error"]["code"] == "voice_too_long"
    assert (await send(gps, ctype="video/mp4")).json()["error"]["code"] == "bad_audio"
    assert (await send(gps, data=b"0" * (2 * 1024 * 1024 + 5))).json()["error"]["code"] == "voice_too_large"


async def test_unread_counts_and_mark_read(world, client_factory):
    op, gps, admin, driver = (await client_factory("operator"), await client_factory("gps"), await client_factory("admin"),
                              await client_factory("driver"))
    r1, r2 = world["requests"][:2]
    await op.post(url(r1, "/text"), json={"text": "1"})
    await op.post(url(r1, "/text"), json={"text": "2"})
    await op.post(url(r2, "/text"), json={"text": "3"})
    u = (await gps.get("/api/v1/chat/unread")).json()
    assert u["total"] == 3 and [(t["thread_id"], t["count"]) for t in u["threads"]] == [(r2, 1), (r1, 2)]
    assert (await op.get("/api/v1/chat/unread")).json()["total"] == 0  # o'z xabarlari hisoblanmaydi
    assert (await driver.get("/api/v1/chat/unread")).json()["total"] == 0  # biriktirilmagan
    assert (await gps.post(url(r1, "/read"))).status_code == 204
    assert (await gps.get("/api/v1/chat/unread")).json()["total"] == 1
    assert (await admin.get("/api/v1/chat/unread")).json()["total"] == 3
    # Javob yozish ham o'qilgan qiladi
    await admin.post(url(r2, "/text"), json={"text": "ok"})
    assert [t["thread_id"] for t in (await admin.get("/api/v1/chat/unread")).json()["threads"]] == [r1]


async def test_old_voice_audio_is_purged(world, client_factory, sessionmaker, app):
    gps = await client_factory("gps")
    rid = world["requests"][0]
    m = (await gps.post(url(rid, "/voice"), data={"duration": "5"}, files={"audio": ("v.ogg", WEBM, "audio/ogg")})).json()
    storage: MemoryStorage = app.state.storage
    assert len(storage.objects) == 1
    async with sessionmaker() as s:
        await s.execute(update(ChatMessage).values(created_at=utcnow() - timedelta(days=91)))
        await s.commit()
        assert await chat_svc.purge_voice(s, storage) == 1
        row = (await s.execute(select(ChatMessage))).scalar_one()
        assert row.expired and row.file_key is None
    assert storage.objects == {}
    d = (await gps.get(url(rid))).json()["items"][0]
    assert d["expired"] and not d["has_audio"]
    assert (await gps.get(f"/api/v1/chat/audio/{m['id']}")).status_code == 404


async def test_driver_template_has_chat(world, sessionmaker):
    from app.core.permissions import template
    from app.models.enums import Role
    assert {"chat.view", "chat.write"} <= set(template(Role.driver))
    async with sessionmaker() as s:
        assert (await s.execute(select(Request).where(Request.status == RequestStatus.new))).first()
