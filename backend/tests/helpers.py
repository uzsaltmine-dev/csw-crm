from tests.conftest import PNG

# Korxona koordinatasidan ~50 m va ~800 m
NEAR = {"lat": 40.6419, "lng": 72.2392}
FAR = {"lat": 40.6487, "lng": 72.2390}


async def open_and_start_shift(gps, driver, driver_id: int, vehicle_id: int) -> dict:
    r = await gps.post("/api/v1/gps/shifts", json={"driver_id": driver_id, "vehicle_id": vehicle_id})
    assert r.status_code == 201, r.text
    shift = r.json()
    r = await driver.post(f"/api/v1/driver/shift/{shift['id']}/start", data={"odometer": "12000", "fuel": "80"},
                          files={"photo": ("car.png", PNG, "image/png")})
    assert r.status_code == 200, r.text
    return r.json()


async def upload(driver, request_id: int, kind: str, coords: dict | None = None):
    return await driver.post(f"/api/v1/driver/requests/{request_id}/files",
                             data={"kind": kind, **{k: str(v) for k, v in (coords or {}).items()}},
                             files={"file": (f"{kind}.png", PNG, "image/png")})


async def fill_act(driver, request_id: int, coords: dict) -> None:
    assert (await upload(driver, request_id, "before", coords)).status_code == 200
    for kind in ("face", "sign"):
        assert (await upload(driver, request_id, kind)).status_code == 200
    assert (await upload(driver, request_id, "after", coords)).status_code == 200
