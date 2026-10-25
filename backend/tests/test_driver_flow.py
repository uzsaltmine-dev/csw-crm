from tests.helpers import FAR, NEAR, fill_act, open_and_start_shift, upload

ACT = {"containers": 3, "volume_m3": 6.5, "note": "Hammasi olib ketildi"}


async def _ready(world, client_factory):
    gps, driver = await client_factory("gps"), await client_factory("driver")
    await open_and_start_shift(gps, driver, world["users"]["driver"], world["vehicles"]["v1"])
    return gps, driver


async def test_assign_creates_naryad_per_provider_and_year(world, client_factory):
    gps, _ = await _ready(world, client_factory)
    ids = world["requests"]
    n1 = (await gps.post(f"/api/v1/gps/requests/{ids[0]}/assign", json={"driver_id": world["users"]["driver"]})).json()["naryad_no"]
    n2 = (await gps.post(f"/api/v1/gps/requests/{ids[1]}/assign", json={"driver_id": world["users"]["driver"]})).json()["naryad_no"]
    year = n1.split("-")[1]
    assert n1 == f"BTE-{year}-00001" and n2 == f"BTE-{year}-00002"


async def test_assign_requires_active_shift_and_same_district(world, client_factory):
    gps = await client_factory("gps")
    rid = world["requests"][0]
    r = await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})
    assert r.json()["error"]["code"] == "driver_no_active_shift"
    r = await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver_b"]})
    assert r.json()["error"]["code"] == "district_mismatch"


async def test_full_flow_done(world, client_factory):
    gps, driver = await _ready(world, client_factory)
    rid = world["requests"][0]
    await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})
    tasks = (await driver.get("/api/v1/driver/tasks")).json()
    assert [t["id"] for t in tasks][0] == rid and tasks[0]["customer"]["stir"] == "305123456"

    assert (await driver.post(f"/api/v1/driver/requests/{rid}/enroute")).json()["status"] == "enroute"
    assert (await driver.post("/api/v1/driver/location", json=NEAR)).status_code == 204
    await fill_act(driver, rid, NEAR)
    tasks = (await driver.get("/api/v1/driver/tasks")).json()
    assert tasks[0]["status"] == "onsite" and set(tasks[0]["files"]) == {"before", "after", "face", "sign"}

    r = await driver.post(f"/api/v1/driver/requests/{rid}/complete", json={**ACT, **NEAR})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["request"]["status"] == "done"
    assert body["act"]["in_radius"] and body["act"]["distance_m"] < 100 and body["act"]["vehicle_plate"] == "60 101 AB"


async def test_outside_radius_is_suspect(world, client_factory):
    gps, driver = await _ready(world, client_factory)
    rid = world["requests"][0]
    await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})
    await driver.post(f"/api/v1/driver/requests/{rid}/enroute")
    await fill_act(driver, rid, FAR)
    body = (await driver.post(f"/api/v1/driver/requests/{rid}/complete", json={**ACT, **FAR})).json()
    assert body["request"]["status"] == "suspect" and body["act"]["distance_m"] > 300


async def test_incomplete_act_rejected(world, client_factory):
    gps, driver = await _ready(world, client_factory)
    rid = world["requests"][0]
    await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})
    await driver.post(f"/api/v1/driver/requests/{rid}/enroute")
    assert (await upload(driver, rid, "before", NEAR)).status_code == 200
    r = await driver.post(f"/api/v1/driver/requests/{rid}/complete", json={**ACT, **NEAR})
    err = r.json()["error"]
    assert r.status_code == 422 and err["code"] == "act_incomplete"
    assert "file:after" in err["message"] and "file:face" in err["message"] and "file:sign" in err["message"]


async def test_photo_order_and_gps_rules(world, client_factory):
    gps, driver = await _ready(world, client_factory)
    rid = world["requests"][0]
    await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})
    await driver.post(f"/api/v1/driver/requests/{rid}/enroute")
    assert (await upload(driver, rid, "after", NEAR)).json()["error"]["code"] == "before_photo_first"
    assert (await upload(driver, rid, "before")).json()["error"]["code"] == "gps_required"


async def test_fail_keeps_request_open_and_blocks_shift_end_until_done(world, client_factory):
    gps, driver = await _ready(world, client_factory)
    rid, rid2 = world["requests"][0], world["requests"][1]
    for x in (rid, rid2):
        await gps.post(f"/api/v1/gps/requests/{x}/assign", json={"driver_id": world["users"]["driver"]})
    shift_id = (await driver.get("/api/v1/driver/shift/current")).json()["id"]
    await driver.post(f"/api/v1/driver/requests/{rid}/enroute")
    r = await driver.post(f"/api/v1/driver/requests/{rid}/fail", json={"reason": "no_waste", "note": "Konteyner bo'sh"})
    assert r.json()["status"] == "failed"
    r = await driver.post(f"/api/v1/driver/shift/{shift_id}/end", json={"odometer": 12010, "fuel": 70})
    assert r.json()["error"]["code"] == "shift_has_active_requests"


async def test_driver_cannot_touch_foreign_request(world, client_factory):
    gps, _ = await _ready(world, client_factory)
    rid = world["requests"][0]
    await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})
    other = await client_factory("driver2")
    await open_and_start_shift(gps, other, world["users"]["driver2"], world["vehicles"]["v2"])
    r = await other.post(f"/api/v1/driver/requests/{rid}/enroute")
    assert r.status_code == 404 and r.json()["error"]["code"] == "request_not_found"


async def test_after_photo_keeps_location_and_accuracy(world, client_factory, sessionmaker):
    from sqlalchemy import select

    from app.models import ActFile
    from app.models.enums import FileKind
    gps, driver = await _ready(world, client_factory)
    rid = world["requests"][0]
    await gps.post(f"/api/v1/gps/requests/{rid}/assign", json={"driver_id": world["users"]["driver"]})
    await driver.post(f"/api/v1/driver/requests/{rid}/enroute")
    assert (await upload(driver, rid, "before", NEAR)).status_code == 200
    r = await upload(driver, rid, "after", {**NEAR, "accuracy": 7.6})
    assert r.status_code == 200 and r.json()["accuracy_m"] == 8 and r.json()["lat"] == NEAR["lat"]
    async with sessionmaker() as s:
        row = (await s.execute(select(ActFile).where(ActFile.request_id == rid, ActFile.kind == FileKind.after))).scalar_one()
        assert (row.lat, row.lng, row.accuracy_m) == (NEAR["lat"], NEAR["lng"], 8)
