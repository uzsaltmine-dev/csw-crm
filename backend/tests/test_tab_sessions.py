"""Demo/sinov rejimi: bitta brauzerning turli tablarida turli rollar (token tab xotirasida, cookie yo'q)."""
import pytest

from app.core.config import get_settings

TAB = {"X-Session-Mode": "tab"}
PWD = "Secret123!"


@pytest.fixture
def tab_mode(monkeypatch):
    monkeypatch.setattr(get_settings(), "tab_sessions", True)


async def _tab_login(client, username: str) -> dict:
    r = await client.post("/api/v1/auth/login", json={"username": username, "password": PWD}, headers=TAB)
    assert r.status_code == 200, r.text
    assert "set-cookie" not in r.headers  # boshqa tablarning sessiyasiga tegmaydi
    return r.json()


async def test_two_roles_in_one_browser(world, client_factory, tab_mode):
    browser = await client_factory()  # bitta cookie jar = bitta brauzer
    admin = await _tab_login(browser, "admin")
    driver = await _tab_login(browser, "driver")
    assert admin["access_token"] and driver["refresh_token"] and admin["role"] == "admin"
    me_a = await browser.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {admin['access_token']}"})
    me_d = await browser.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {driver['access_token']}"})
    assert me_a.json()["username"] == "admin" and me_d.json()["username"] == "driver"
    assert (await browser.get("/api/v1/auth/me")).status_code == 401  # cookie yozilmagan
    # Har tab o'z tokenini yangilaydi
    r = await browser.post("/api/v1/auth/refresh", json={"refresh_token": driver["refresh_token"]}, headers=TAB)
    assert r.status_code == 200 and r.json()["username"] == "driver" and r.json()["access_token"]
    # Bearer bilan yozish so'rovi (CSRF sarlavhasisiz ham) ishlaydi
    r = await browser.put("/api/v1/admin/settings", json={"gps_radius_m": 200},
                          headers={"Authorization": f"Bearer {admin['access_token']}", "X-Requested-With": ""})
    assert r.status_code == 200


async def test_config_endpoint(world, client_factory, tab_mode):
    c = await client_factory()
    assert (await c.get("/api/v1/auth/config")).json()["tab_sessions"] is True


async def test_tab_header_ignored_when_disabled(world, client_factory):
    c = await client_factory()
    r = await c.post("/api/v1/auth/login", json={"username": "admin", "password": PWD}, headers=TAB)
    assert r.status_code == 200 and r.json()["access_token"] is None and "access_token" in r.headers.get("set-cookie", "")
    assert (await c.get("/api/v1/auth/config")).json()["tab_sessions"] is False
    r = await c.post("/api/v1/auth/refresh", json={"refresh_token": "x"}, headers=TAB)  # body e'tiborsiz — cookie ishlatiladi
    assert r.status_code == 200
