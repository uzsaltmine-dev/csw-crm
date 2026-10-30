"""Boshlang'ich ma'lumotlar: viloyatlar, xizmat ko'rsatuvchilar, 12 tuman, mashinalar, foydalanuvchilar, namunaviy korxonalar.

Ishga tushirish:  python -m app.seed
Parol SEED_PASSWORD muhit o'zgaruvchisidan olinadi (bo'lmasa: ChangeMe123!). Qayta ishga tushirilsa hech narsa qo'shmaydi.
"""
import asyncio
import os
from datetime import date, timedelta

from sqlalchemy import select

from app.core.permissions import apply_template
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.services.schedule import today as schedule_today
from app.models import AppSetting, Contract, Customer, District, Provider, Region, ChatMessage, Request, RequestEvent, User, VehiclePosition, WorkSchedule, UserDistrict, Vehicle
from app.db.base import utcnow
from app.models.enums import ContractType, LocationStatus, RequestStatus, Role, WasteType

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
        # Manager va yurist — barcha 12 tuman (pastda biriktiriladi)
        manager = User(username="manager", password_hash=pwd, full_name="Manager", role=Role.manager)
        legal = User(username="legal", password_hash=pwd, full_name="Yuridik bo'lim xodimi", role=Role.legal)
        apply_template(manager)
        apply_template(legal)
        db.add_all([manager, legal])
        district_ids: list[int] = []
        chat_demo: tuple[int, User] | None = None
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
                district_ids.append(d.id)
                gps = User(username=f"gps{n}", password_hash=pwd, full_name=f"GPS xodimi — {d_name}", role=Role.gps, district_id=d.id)
                apply_template(gps)
                db.add(gps)
                for k in (1, 2):
                    veh = Vehicle(plate=f"{plate_code} {n:02d}{k} {code[:2]}", model="ISUZU NQR", district_id=d.id)
                    drv = User(username=f"driver{n}{k}", password_hash=pwd, full_name=f"Haydovchi {n}-{k}",
                               phone=f"+998 90 000-{n:02d}-{k:02d}", role=Role.driver, district_id=d.id)
                    apply_template(drv)  # yozishma ruxsatlari
                    db.add_all([veh, drv])
                    await db.flush()
                    # Bugungi ish jadvali: 1-mashina — yuridik bo'lim, 2-mashina — mahallalar (jismoniy abonentlar).
                    # Joylashuv (GPS-monitoring ulanmaguncha namunaviy): 1-mashina korxonaga yaqinroq.
                    db.add(WorkSchedule(day=schedule_today(), district_id=d.id, vehicle_id=veh.id, driver_id=drv.id,
                                        service="legal" if k == 1 else "individual",
                                        mahallas=None if k == 1 else "Bog'bon, Navbahor mahallalari"))
                    db.add(VehiclePosition(vehicle_id=veh.id, lat=lat + 0.01 * k, lng=lng - 0.008 * k, at=utcnow(), source="demo"))
                c = Customer(fixed_no=f"A-{100 + n:04d}", stir=f"{300000000 + n * 1111:09d}", name=f"\"Namuna {n}\" MChJ",
                             name_key=f"namuna {n} mchj", location_status=LocationStatus.confirmed, activity_type="Savdo",
                             director="Namuna rahbar", phone="+998 91 111-11-11", district_id=d.id,
                             address="Mustaqillik ko'chasi, 1-uy", lat=lat + 0.002, lng=lng + 0.002)
                db.add(c)
                await db.flush()
                ct = Contract(customer_id=c.id, number=f"SH-2026/{n:04d}", signed_on=date(2026, 1, 15),
                              type=ContractType.monthly, price=1_200_000, valid_from=date.today() - timedelta(days=30), valid_to=date.today() + timedelta(days=365))
                db.add(ct)
                await db.flush()
                now = utcnow()
                for k in range(REQUESTS_PER_DISTRICT):
                    r = Request(customer_id=c.id, contract_id=ct.id, district_id=d.id, waste_type=WasteType.household,
                                volume_estimate=6, preferred_time="08:00–12:00", note=f"Namunaviy ariza {k + 1}",
                                due_at=now + timedelta(hours=72), is_repeat=k == REQUESTS_PER_DISTRICT - 1,
                                caller_name="Namuna qo'ng'iroq qiluvchi", caller_phone="+998 91 111-11-11")
                    db.add(r)
                    await db.flush()
                    r.number = f"M-{r.id:06d}"
                    db.add(RequestEvent(request_id=r.id, status=RequestStatus.new, created_at=now, note="namunaviy ariza"))
                    if d_name == "Asaka tumani" and k == 0:
                        chat_demo = (r.id, gps)
                # Statistika uchun tarix: 6 kun oldin bajarilgan va 4 kun oldin ochilib muddati o'tgan ariza
                for days, status in ((6, RequestStatus.done), (4, RequestStatus.new)):
                    created = now - timedelta(days=days)
                    r = Request(customer_id=c.id, contract_id=ct.id, district_id=d.id, waste_type=WasteType.household,
                                volume_estimate=6, note="Namunaviy (tarix)", status=status, created_at=created,
                                due_at=created + timedelta(hours=72), finished_at=created + timedelta(hours=20) if status == RequestStatus.done else None,
                                # Asakada muddati o'tgan ariza Vaziyat paneliga demo ishga tushgach 10 daqiqa ichida tushadi
                                overdue_notified=d_name != "Asaka tumani")
                    db.add(r)
                    await db.flush()
                    r.number = f"M-{r.id:06d}"
                    db.add(RequestEvent(request_id=r.id, status=RequestStatus.new, created_at=created))
                    if r.finished_at:
                        db.add(RequestEvent(request_id=r.id, status=RequestStatus.done, created_at=r.finished_at))
                # Kartasi to'liq bo'lmagan korxona (STIR, shartnoma, koordinata yo'q) — assenizator arizasi biriktirilmaydi,
                # yurist STIR va shartnoma kiritgach biriktiriladi; birinchi tashrifdan keyin Manager koordinatani tasdiqlaydi
                c2 = Customer(fixed_no=f"A-{200 + n:04d}", name=f"\"Yangi mijoz {n}\" MChJ", name_key=f"yangi mijoz {n} mchj",
                              location_status=LocationStatus.none, activity_type="Umumiy ovqatlanish", phone="+998 93 222-22-22",
                              district_id=d.id, address="Navoiy ko'chasi, 5-uy", source="excel")
                db.add(c2)
                await db.flush()
                r = Request(customer_id=c2.id, district_id=d.id, waste_type=WasteType.septic, volume_estimate=4,
                            note="Assenizator: hojatxona chuquri to'lgan", due_at=utcnow() + timedelta(hours=72))
                db.add(r)
                await db.flush()
                r.number = f"M-{r.id:06d}"
                db.add(RequestEvent(request_id=r.id, status=RequestStatus.new, created_at=utcnow()))
        # Call-center operatori (demo: barcha tumanlar)
        operator = User(username="operator", password_hash=pwd, full_name="Call-center operatori", role=Role.operator)
        apply_template(operator)
        db.add(operator)
        await db.flush()
        db.add_all([UserDistrict(user_id=u.id, district_id=d) for u in (manager, legal, operator) for d in district_ids])
        # Yozishma namunasi: Asakadagi birinchi arizada operator va GPS xodimi (gps4)
        if chat_demo:
            rid, gps_user = chat_demo
            for author, text in ((operator, "Mijoz so'radi: mashina soat 14:00 dan keyin kelsin, darvoza orqa tomonda."),
                                 (gps_user, "Tushunarli, haydovchiga yetkazaman."),
                                 (operator, "Rahmat! Mas'ul shaxs telefoni: +998 91 111-11-11")):
                db.add(ChatMessage(thread_type="request", thread_id=rid, author_id=author.id, kind="text", text=text))
        await db.commit()
        print("Seed tayyor: admin, manager, legal, operator, gps1..gps12, driver11..driver122")


if __name__ == "__main__":
    asyncio.run(seed())
