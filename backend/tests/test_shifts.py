from tests.conftest import PNG
from tests.helpers import open_and_start_shift


async def test_shift_lifecycle_and_totals(world, client_factory):
    gps, driver = await client_factory("gps"), await client_factory("driver")
    u, v = world["users"], world["vehicles"]
    shift = await open_and_start_shift(gps, driver, u["driver"], v["v1"])
    assert shift["status"] == "active" and shift["vehicle"]["plate"] == "60 101 AB"

    cur = (await driver.get("/api/v1/driver/shift/current")).json()
    assert cur["id"] == shift["id"]

    r = await driver.post(f"/api/v1/driver/shift/{shift['id']}/end", json={"odometer": 12085, "fuel": 52.5})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "closed" and body["distance_km"] == 85 and float(body["fuel_used"]) == 27.5
    assert (await driver.get("/api/v1/driver/shift/current")).json() is None


async def test_vehicle_cannot_be_in_two_open_shifts(world, client_factory):
    gps = await client_factory("gps")
    u, v = world["users"], world["vehicles"]
    assert (await gps.post("/api/v1/gps/shifts", json={"driver_id": u["driver"], "vehicle_id": v["v1"]})).status_code == 201
    r = await gps.post("/api/v1/gps/shifts", json={"driver_id": u["driver2"], "vehicle_id": v["v1"]})
    assert r.status_code == 409 and r.json()["error"]["code"] == "vehicle_busy"
    r = await gps.post("/api/v1/gps/shifts", json={"driver_id": u["driver"], "vehicle_id": v["v2"]})
    assert r.json()["error"]["code"] == "driver_has_open_shift"


async def test_gps_limited_to_own_district(world, client_factory):
    gps = await client_factory("gps")
    r = await gps.post("/api/v1/gps/shifts", json={"driver_id": world["users"]["driver_b"], "vehicle_id": world["vehicles"]["vb"]})
    assert r.status_code == 403


async def test_odometer_cannot_decrease(world, client_factory):
    gps, driver = await client_factory("gps"), await client_factory("driver")
    shift = await open_and_start_shift(gps, driver, world["users"]["driver"], world["vehicles"]["v1"])
    r = await driver.post(f"/api/v1/driver/shift/{shift['id']}/end", json={"odometer": 11999, "fuel": 10})
    assert r.status_code == 422 and r.json()["error"]["code"] == "odometer_decreased"


async def test_start_requires_image(world, client_factory):
    gps, driver = await client_factory("gps"), await client_factory("driver")
    s = (await gps.post("/api/v1/gps/shifts", json={"driver_id": world["users"]["driver"], "vehicle_id": world["vehicles"]["v1"]})).json()
    r = await driver.post(f"/api/v1/driver/shift/{s['id']}/start", data={"odometer": "1", "fuel": "1"},
                          files={"photo": ("x.txt", PNG, "text/plain")})
    assert r.status_code == 422 and r.json()["error"]["code"] == "bad_file_type"


async def test_free_vehicles_list(world, client_factory):
    gps, driver = await client_factory("gps"), await client_factory("driver")
    await open_and_start_shift(gps, driver, world["users"]["driver"], world["vehicles"]["v1"])
    plates = [v["plate"] for v in (await gps.get("/api/v1/gps/vehicles")).json()]
    assert plates == ["60 102 AB"]
