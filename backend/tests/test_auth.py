from tests.conftest import HEADERS, PASSWORD


async def test_login_sets_cookies_and_me(world, client_factory):
    c = await client_factory("driver")
    assert "access_token" in c.cookies
    r = await c.get("/api/v1/auth/me")
    assert r.status_code == 200 and r.json()["role"] == "driver"


async def test_wrong_password_then_lock(world, client_factory):
    c = await client_factory()
    for _ in range(5):
        r = await c.post("/api/v1/auth/login", json={"username": "driver", "password": "wrong"})
        assert r.status_code == 401
    r = await c.post("/api/v1/auth/login", json={"username": "driver", "password": PASSWORD})
    assert r.status_code == 423 and r.json()["error"]["code"] == "account_locked"


async def test_refresh_and_logout(world, client_factory):
    c = await client_factory("driver")
    assert (await c.post("/api/v1/auth/refresh")).status_code == 200
    assert (await c.post("/api/v1/auth/logout")).status_code == 204


async def test_csrf_header_required(world, client_factory):
    c = await client_factory()
    r = await c.post("/api/v1/auth/login", json={"username": "driver", "password": PASSWORD},
                     headers={"X-Requested-With": ""})
    assert r.status_code == 403 and r.json()["error"]["code"] == "csrf"
    assert HEADERS  # sarlavha bilan login conftest'da sinalgan


async def test_role_guard(world, client_factory):
    driver = await client_factory("driver")
    r = await driver.post("/api/v1/gps/shifts", json={"driver_id": 1, "vehicle_id": 1})
    assert r.status_code == 403
