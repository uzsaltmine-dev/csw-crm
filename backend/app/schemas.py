from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ContractType, FailReason, FileKind, RequestStatus, Role, ShiftStatus, WasteType


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- auth ---
class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class UserOut(ORM):
    id: int
    username: str
    full_name: str
    phone: str | None
    role: Role
    district_id: int | None
    language: str
    must_change_password: bool = False


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


# --- admin ---
USERNAME_PATTERN = r"^[a-z0-9_.]{3,50}$"


class AdminUserOut(UserOut):
    is_active: bool
    locked_until: datetime | None
    created_at: datetime


class UserCreateIn(BaseModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    full_name: str = Field(min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    role: Role
    district_id: int | None = None
    language: str = Field(default="uz", pattern=r"^(uz|cy|ru|en)$")
    password: str = Field(min_length=1, max_length=128)  # vaqtinchalik — birinchi kirishda almashtiriladi


class UserUpdateIn(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=150)
    phone: str | None = Field(default=None, max_length=30)
    role: Role | None = None
    district_id: int | None = None
    language: str | None = Field(default=None, pattern=r"^(uz|cy|ru|en)$")
    is_active: bool | None = None


class PasswordResetIn(BaseModel):
    password: str = Field(min_length=1, max_length=128)


class RegionOut(ORM):
    id: int
    name: str


class DistrictOut(ORM):
    id: int
    name: str
    region_id: int
    is_active: bool


class DistrictIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    region_id: int


class DistrictUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    is_active: bool | None = None


class AdminVehicleOut(ORM):
    id: int
    plate: str
    model: str | None
    district_id: int
    is_active: bool


class VehicleIn(BaseModel):
    plate: str = Field(min_length=4, max_length=20)
    model: str | None = Field(default=None, max_length=80)
    district_id: int


class VehicleUpdateIn(BaseModel):
    plate: str | None = Field(default=None, min_length=4, max_length=20)
    model: str | None = Field(default=None, max_length=80)
    district_id: int | None = None
    is_active: bool | None = None


class SettingsOut(BaseModel):
    gps_radius_m: int


class SettingsIn(BaseModel):
    gps_radius_m: int = Field(ge=100, le=300)


# --- shifts ---
class VehicleOut(ORM):
    id: int
    plate: str
    model: str | None
    district_id: int


class ShiftOpenIn(BaseModel):
    driver_id: int
    vehicle_id: int


class ShiftEndIn(BaseModel):
    odometer: int = Field(ge=0)
    fuel: Decimal = Field(ge=0, max_digits=6, decimal_places=1)


class ShiftOut(ORM):
    id: int
    status: ShiftStatus
    driver_id: int
    district_id: int
    vehicle: VehicleOut
    started_at: datetime | None
    ended_at: datetime | None
    odometer_start: int | None
    odometer_end: int | None
    fuel_start: Decimal | None
    fuel_end: Decimal | None
    distance_km: int | None = None
    fuel_used: Decimal | None = None

    @classmethod
    def build(cls, s) -> "ShiftOut":
        out = cls.model_validate(s)
        if s.odometer_end is not None and s.odometer_start is not None:
            out.distance_km = s.odometer_end - s.odometer_start
        if s.fuel_end is not None and s.fuel_start is not None:
            out.fuel_used = Decimal(s.fuel_start) - Decimal(s.fuel_end)
        return out


# --- requests / driver ---
class CustomerOut(ORM):
    id: int
    fixed_no: str
    stir: str
    name: str
    director: str | None
    phone: str | None
    address: str | None
    district_id: int
    lat: float
    lng: float


class ContractOut(ORM):
    id: int
    number: str
    signed_on: date | None
    type: ContractType


class RequestOut(ORM):
    id: int
    number: str | None
    status: RequestStatus
    waste_type: WasteType
    volume_estimate: Decimal | None
    preferred_time: str | None
    note: str | None
    naryad_no: str | None
    district_id: int
    driver_id: int | None
    created_at: datetime
    assigned_at: datetime | None
    customer: CustomerOut
    contract: ContractOut | None


class DriverTaskOut(RequestOut):
    files: list[FileKind] = []


class LocationIn(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    accuracy_m: float | None = None


class CompleteIn(BaseModel):
    containers: int = Field(ge=1, le=100)
    volume_m3: Decimal = Field(gt=0, le=1000, max_digits=8, decimal_places=2)
    note: str = Field(min_length=1, max_length=2000)
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class ActOut(ORM):
    containers: int
    volume_m3: Decimal
    distance_m: int
    radius_m: int
    in_radius: bool
    vehicle_plate: str
    completed_at: datetime


class CompleteOut(BaseModel):
    request: RequestOut
    act: ActOut


class FailIn(BaseModel):
    reason: FailReason
    note: str | None = Field(default=None, max_length=2000)


class FileOut(ORM):
    id: int
    kind: FileKind
    size_bytes: int


class AssignIn(BaseModel):
    driver_id: int
