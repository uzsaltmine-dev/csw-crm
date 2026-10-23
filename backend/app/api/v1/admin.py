"""Admin paneli: xodimlar, tumanlar, mashinalar, sozlamalar. Yozish — faqat admin, o'qish — admin va manager."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB, require_roles
from app.models import User
from app.models.enums import Role
from app.repositories import catalog
from app.repositories import settings as settings_repo
from app.schemas import (AdminUserOut, AdminVehicleOut, DistrictIn, DistrictOut, DistrictUpdateIn, PasswordResetIn,
                         RegionOut, SettingsIn, SettingsOut, UserCreateIn, UserUpdateIn, VehicleIn, VehicleUpdateIn)
from app.services import admin_service

router = APIRouter(prefix="/admin", tags=["admin"])
Reader = Depends(require_roles(Role.admin, Role.manager))
Writer = Depends(require_roles(Role.admin))


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
async def regions(_: User = Reader, db: AsyncSession = DB):
    return await catalog.regions(db)


@router.get("/districts", response_model=list[DistrictOut])
async def districts(_: User = Reader, db: AsyncSession = DB):
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
