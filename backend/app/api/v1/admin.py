"""Admin paneli: xodimlar, tumanlar, mashinalar, sozlamalar. Yozish — faqat admin, o'qish — admin va manager."""
from dataclasses import asdict

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_roles
from app.core.errors import invalid
from app.models import User
from app.models.enums import Role
from app.repositories import catalog
from app.repositories import customers as customers_repo
from app.repositories import settings as settings_repo
from app.schemas import (
    AdminUserOut,
    AdminVehicleOut,
    DistrictIn,
    DistrictOut,
    DistrictUpdateIn,
    ImportBatchOut,
    ImportResultOut,
    PasswordResetIn,
    RegionOut,
    SettingsIn,
    SettingsOut,
    UserCreateIn,
    UserUpdateIn,
    VehicleIn,
    VehicleUpdateIn,
)
from app.services import admin_service, customer_import

router = APIRouter(prefix="/admin", tags=["admin"])
Reader = Depends(require_roles(Role.admin, Role.manager))
Writer = Depends(require_roles(Role.admin))
# Ma'lumotnomalar (viloyat/tuman) — korxonalar bilan ishlaydigan yuridik bo'lim ham o'qiydi
RefReader = Depends(require_roles(Role.admin, Role.manager, Role.legal))


@router.get("/users", response_model=list[AdminUserOut])
async def users(role: Role | None = None, district_id: int | None = None, active: bool | None = Query(None),
                _: User = Reader, db: AsyncSession = DB):
    return await catalog.list_users(db, role, district_id, active)


@router.post("/users", response_model=AdminUserOut, status_code=201)
async def create_user(body: UserCreateIn, _: User = Writer, db: AsyncSession = DB):
    return await admin_service.create_user(db, body)


@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(user_id: int, body: UserUpdateIn, admin: User = Writer, db: AsyncSession = DB):
    return await admin_service.update_user(db, admin, user_id, body)


@router.post("/users/{user_id}/reset-password", response_model=AdminUserOut)
async def reset_password(user_id: int, body: PasswordResetIn, _: User = Writer, db: AsyncSession = DB):
    return await admin_service.reset_password(db, user_id, body.password)


@router.get("/regions", response_model=list[RegionOut])
async def regions(_: User = RefReader, db: AsyncSession = DB):
    return await catalog.regions(db)


@router.get("/districts", response_model=list[DistrictOut])
async def districts(_: User = RefReader, db: AsyncSession = DB):
    return await catalog.districts(db)


@router.post("/districts", response_model=DistrictOut, status_code=201)
async def create_district(body: DistrictIn, _: User = Writer, db: AsyncSession = DB):
    return await admin_service.create_district(db, body)


@router.patch("/districts/{district_id}", response_model=DistrictOut)
async def update_district(district_id: int, body: DistrictUpdateIn, _: User = Writer, db: AsyncSession = DB):
    return await admin_service.update_district(db, district_id, body)


@router.get("/vehicles", response_model=list[AdminVehicleOut])
async def vehicles(district_id: int | None = None, _: User = Reader, db: AsyncSession = DB):
    return await catalog.vehicles(db, district_id)


@router.post("/vehicles", response_model=AdminVehicleOut, status_code=201)
async def create_vehicle(body: VehicleIn, _: User = Writer, db: AsyncSession = DB):
    return await admin_service.create_vehicle(db, body)


@router.patch("/vehicles/{vehicle_id}", response_model=AdminVehicleOut)
async def update_vehicle(vehicle_id: int, body: VehicleUpdateIn, _: User = Writer, db: AsyncSession = DB):
    return await admin_service.update_vehicle(db, vehicle_id, body)


@router.get("/settings", response_model=SettingsOut)
async def get_settings(_: User = Reader, db: AsyncSession = DB):
    return SettingsOut(gps_radius_m=await settings_repo.gps_radius(db))


@router.put("/settings", response_model=SettingsOut)
async def put_settings(body: SettingsIn, _: User = Writer, db: AsyncSession = DB):
    return SettingsOut(gps_radius_m=await admin_service.set_gps_radius(db, body.gps_radius_m))


MAX_IMPORT_BYTES = 10 * 1024 * 1024


@router.post("/import/customers", response_model=ImportResultOut)
async def import_customers(file: UploadFile = File(...), dry_run: bool = True, admin: User = Writer, db: AsyncSession = DB):
    """Call-center Excel fayli. Avval dry_run=true (tahlil, bazaga yozilmaydi), keyin dry_run=false."""
    if not (file.filename or "").lower().endswith(".xlsx"):
        raise invalid("bad_excel", "Faqat .xlsx formatidagi Excel fayl qabul qilinadi")
    content = await file.read(MAX_IMPORT_BYTES + 1)
    if len(content) > MAX_IMPORT_BYTES:
        raise invalid("file_too_large", "Fayl hajmi 10 MB dan oshmasin")
    result = await customer_import.run(db, admin, file.filename or "import.xlsx", content, dry_run)
    return ImportResultOut(**asdict(result), dry_run=dry_run)


@router.get("/import/batches", response_model=list[ImportBatchOut])
async def import_batches(_: User = Reader, db: AsyncSession = DB):
    return await customers_repo.import_batches(db)
