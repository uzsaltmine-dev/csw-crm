"""Boshlang'ich ma'lumotlar: viloyatlar, xizmat ko'rsatuvchilar, 12 tuman, mashinalar, foydalanuvchilar, namunaviy korxonalar.

Ishga tushirish:  python -m app.seed
Parol SEED_PASSWORD muhit o'zgaruvchisidan olinadi (bo'lmasa: ChangeMe123!). Qayta ishga tushirilsa hech narsa qo'shmaydi.
"""
import asyncio
import os
from datetime import date

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models import AppSetting, Contract, Customer, District, Provider, Region, Request, User, Vehicle
from app.models.enums import ContractType, Role, WasteType

REGIONS = {
    "Andijon viloyati": ("Bio Tex Eko", "BTE", "60", [
        ("Andijon shahri", 40.7821, 72.3442), ("Andijon tumani", 40.7480, 72.4310),
        ("Oltinko'l tumani", 40.8030, 72.1700), ("Asaka tumani", 40.6415, 72.2390)]),
    "Surxondaryo viloyati": ("Bio Texno Klaster", "BTK", "75", [
        ("Termiz shahri", 37.2242, 67.2783), ("Termiz tumani", 37.3010, 67.3420), ("Angor tumani", 37.4620, 67.1510),
        ("Uzun tumani", 38.3680, 68.0020), ("Sariosiyo tumani", 38.4130, 67.9580)]),
    "Qashqadaryo viloyati": ("Bisay", "BSY", "70", [
        ("Shahrisabz shahri", 39.0570, 66.8340), ("Shahrisabz tumani", 39.0010, 66.9020), ("Kitob tumani", 39.1180, 66.8820)]),
}


REQUESTS_PER_DISTRICT = 5  # demo: GPS xodimi bir necha marta biriktirib sinashi uchun


async def seed() -> None:
    pwd = hash_password(os.getenv("SEED_PASSWORD", "ChangeMe123!"))
    async with SessionLocal() as db:
        if (await db.execute(select(Region))).first():
            print("Seed allaqachon bajarilgan — o'tkazib yuborildi")
            return
        db.add(AppSetting(key="gps_radius_m", value="300"))
        db.add(User(username="admin", password_hash=pwd, full_name="Administrator", role=Role.admin))
        db.add(User(username="manager", password_hash=pwd, full_name="Manager", role=Role.manager))
        n = 0
        for region_name, (prov_name, code, plate_code, districts) in REGIONS.items():
            region = Region(name=region_name)
            db.add(region)
            await db.flush()
            db.add(Provider(name=prov_name, code=code, region_id=region.id))
            for d_name, lat, lng in districts:
                n += 1
                d = District(name=d_name, region_id=region.id)
                db.add(d)
                await db.flush()
                db.add(User(username=f"gps{n}", password_hash=pwd, full_name=f"GPS xodimi — {d_name}", role=Role.gps, district_id=d.id))
                for k in (1, 2):
                    db.add(Vehicle(plate=f"{plate_code} {n:02d}{k} {code[:2]}", model="ISUZU NQR", district_id=d.id))
                    db.add(User(username=f"driver{n}{k}", password_hash=pwd, full_name=f"Haydovchi {n}-{k}",
                                phone=f"+998 90 000-{n:02d}-{k:02d}", role=Role.driver, district_id=d.id))
                c = Customer(fixed_no=f"A-{100 + n:04d}", stir=f"{300000000 + n * 1111:09d}", name=f"\"Namuna {n}\" MChJ",
                             director="Namuna rahbar", phone="+998 91 111-11-11", district_id=d.id,
                             address="Mustaqillik ko'chasi, 1-uy", lat=lat + 0.002, lng=lng + 0.002)
                db.add(c)
                await db.flush()
                ct = Contract(customer_id=c.id, number=f"SH-2026/{n:04d}", signed_on=date(2026, 1, 15),
                              type=ContractType.monthly, price=1_200_000, valid_from=date(2026, 1, 1), valid_to=date(2026, 12, 31))
                db.add(ct)
                await db.flush()
                for k in range(REQUESTS_PER_DISTRICT):
                    r = Request(customer_id=c.id, contract_id=ct.id, district_id=d.id, waste_type=WasteType.household,
                                volume_estimate=6, preferred_time="08:00–12:00", note=f"Namunaviy ariza {k + 1}")
                    db.add(r)
                    await db.flush()
                    r.number = f"AR-{r.id:06d}"
        await db.commit()
        print("Seed tayyor: admin, manager, gps1..gps12, driver11..driver122")


if __name__ == "__main__":
    asyncio.run(seed())
