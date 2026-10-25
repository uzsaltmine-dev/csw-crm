import os

os.environ.setdefault("JWT_SECRET", "test-secret")

from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.permissions import apply_template
from app.core.security import hash_password
from app.db.session import get_session
from app.main import create_app
from app.models import Base, Contract, Customer, District, Provider, Region, Request, User, Vehicle
from app.models.enums import ContractType, LocationStatus, Role
from app.services.storage import MemoryStorage

PASSWORD = "Secret123!"
HEADERS = {"X-Requested-With": "csw"}
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64


@pytest.fixture
async def sessionmaker(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def world(sessionmaker):
    """Andijon (BTE) va Surxondaryo (BTK); A tumanida GPS xodimi, ikki haydovchi, ikki mashina, korxona va yangi ariza."""
    pwd = hash_password(PASSWORD)
    async with sessionmaker() as db:
        r1, r2 = Region(name="Andijon viloyati"), Region(name="Surxondaryo viloyati")
        db.add_all([r1, r2]); await db.flush()
        db.add_all([Provider(name="Bio Tex Eko", code="BTE", region_id=r1.id), Provider(name="Bio Texno Klaster", code="BTK", region_id=r2.id)])
        da, db_ = District(name="Asaka tumani", region_id=r1.id), District(name="Termiz shahri", region_id=r2.id)
        db.add_all([da, db_]); await db.flush()
        users = {
            "gps": User(username="gps", password_hash=pwd, full_name="GPS", role=Role.gps, district_id=da.id),
            "driver": User(username="driver", password_hash=pwd, full_name="Haydovchi A", role=Role.driver, district_id=da.id),
            "driver2": User(username="driver2", password_hash=pwd, full_name="Haydovchi A2", role=Role.driver, district_id=da.id),
            "driver_b": User(username="driver_b", password_hash=pwd, full_name="Haydovchi B", role=Role.driver, district_id=db_.id),
            "manager": User(username="manager", password_hash=pwd, full_name="Manager", role=Role.manager),
            "admin": User(username="admin", password_hash=pwd, full_name="Admin", role=Role.admin),
            "legal": User(username="legal", password_hash=pwd, full_name="Yurist", role=Role.legal),
        }
        for u in users.values():
            apply_template(u, [da.id, db_.id])
        db.add_all(users.values())
        v1, v2 = Vehicle(plate="60 101 AB", district_id=da.id), Vehicle(plate="60 102 AB", district_id=da.id)
        vb = Vehicle(plate="75 201 BA", district_id=db_.id)
        db.add_all([v1, v2, vb]); await db.flush()
        cust = Customer(fixed_no="A-0101", stir="305123456", name="\"Asaka Avto\" MChJ", name_key="asaka avto mchj",
                        district_id=da.id, lat=40.6415, lng=72.2390, location_status=LocationStatus.confirmed)
        db.add(cust); await db.flush()
        ct = Contract(customer_id=cust.id, number="SH-2026/0001", type=ContractType.monthly,
                      valid_from=date.today() - timedelta(days=30), valid_to=date.today() + timedelta(days=365))
        db.add(ct); await db.flush()
        reqs = []
        for i in range(3):
            r = Request(customer_id=cust.id, contract_id=ct.id, district_id=da.id)
            db.add(r); await db.flush(); r.number = f"AR-{r.id:06d}"; reqs.append(r)
        await db.commit()
        return {"users": {k: u.id for k, u in users.items()}, "vehicles": {"v1": v1.id, "v2": v2.id, "vb": vb.id},
                "districts": {"a": da.id, "b": db_.id}, "requests": [r.id for r in reqs], "customer": cust}


@pytest.fixture
async def app(sessionmaker):
    application = create_app(storage=MemoryStorage())
    application.state.storage = MemoryStorage()  # ASGITransport lifespan'ni ishga tushirmaydi

    async def override():
        async with sessionmaker() as s:
            yield s

    application.dependency_overrides[get_session] = override
    return application


@pytest.fixture
def client_factory(app):
    clients = []

    async def make(username: str | None = None) -> AsyncClient:
        c = AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=HEADERS)
        clients.append(c)
        if username:
            r = await c.post("/api/v1/auth/login", json={"username": username, "password": PASSWORD})
            assert r.status_code == 200, r.text
        return c

    yield make
