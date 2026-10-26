"""Barcha modellar shu yerdan import qilinadi (Alembic autogenerate ham shuni ishlatadi)."""
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Float, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, false as sa_false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, utcnow
from app.models.enums import (AppealStatus, ContractType, FailReason, FileKind, LocationStatus, RequestSource, RequestStatus, Role,
                              ShiftStatus, SituationLevel, WasteType)


def enum_col(enum_cls):
    # VARCHAR sifatida saqlanadi: yangi qiymat qo'shish migratsiyasiz ishlaydi
    return SAEnum(enum_cls, native_enum=False, length=20, validate_strings=True)


class Region(Base):
    __tablename__ = "regions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Provider(Base):
    """Xizmat ko'rsatuvchi kompaniya (viloyat bo'yicha). `code` avtonaryad raqamida ishlatiladi."""
    __tablename__ = "providers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150))
    code: Mapped[str] = mapped_column(String(10), unique=True)
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), unique=True)
    region: Mapped[Region] = relationship()


class District(Base):
    __tablename__ = "districts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    region_id: Mapped[int] = mapped_column(ForeignKey("regions.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Tuman GPS radiusi (100–300 m); bo'sh bo'lsa umumiy sozlama ishlaydi
    gps_radius_m: Mapped[int | None] = mapped_column(Integer)
    region: Mapped[Region] = relationship()


class UserDistrict(Base):
    """Manager, yurist va operator uchun tumanlar doirasi (bir nechta bo'lishi mumkin)."""
    __tablename__ = "user_districts"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), primary_key=True)


class UserPermission(TimestampMixin, Base):
    """Xodimga berilgan ruxsat (masalan, "customers.edit"). Admin uchun yozilmaydi — admin hammasiga ega."""
    __tablename__ = "user_permissions"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    code: Mapped[str] = mapped_column(String(40), primary_key=True)
    granted_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    role: Mapped[Role] = mapped_column(enum_col(Role), index=True)
    # Haydovchi va GPS xodimi uchun: qaysi tumanga biriktirilgan
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"), index=True)
    language: Mapped[str] = mapped_column(String(5), default="uz")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Admin bergan vaqtinchalik paroldan keyin birinchi kirishda almashtirish shart
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime)
    # Manager yaratgan xodim admin tasdiqlamaguncha "pending" (kira olmaydi)
    approval_status: Mapped[str] = mapped_column(String(10), default="approved", server_default="approved")
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    district: Mapped[District | None] = relationship()
    # Xodimlar soni kichik (~20) — ruxsat va doira har doim birga yuklanadi
    perm_rows: Mapped[list[UserPermission]] = relationship(lazy="selectin", cascade="all, delete-orphan",
                                                           foreign_keys=[UserPermission.user_id])
    district_rows: Mapped[list[UserDistrict]] = relationship(lazy="selectin", cascade="all, delete-orphan")

    @property
    def permissions(self) -> list[str]:
        from app.core.permissions import ALL_CODES
        return sorted(ALL_CODES) if self.role == Role.admin else sorted(p.code for p in self.perm_rows)

    @property
    def district_ids(self) -> list[int]:
        """Ishlash doirasi: GPS/haydovchi — bitta tuman; manager/yurist/operator — biriktirilgan tumanlar."""
        ids = {d.district_id for d in self.district_rows}
        if self.district_id:
            ids.add(self.district_id)
        return sorted(ids)

    def can(self, code: str) -> bool:
        return self.role == Role.admin or any(p.code == code for p in self.perm_rows)


class Vehicle(Base):
    __tablename__ = "vehicles"
    id: Mapped[int] = mapped_column(primary_key=True)
    plate: Mapped[str] = mapped_column(String(20), unique=True)
    model: Mapped[str | None] = mapped_column(String(80))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Shift(TimestampMixin, Base):
    """Kunlik smena: GPS xodimi haydovchini mashina bilan juftlaydi."""
    __tablename__ = "shifts"
    id: Mapped[int] = mapped_column(primary_key=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    opened_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[ShiftStatus] = mapped_column(enum_col(ShiftStatus), default=ShiftStatus.opened, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)
    odometer_start: Mapped[int | None] = mapped_column(Integer)
    odometer_end: Mapped[int | None] = mapped_column(Integer)
    fuel_start: Mapped[float | None] = mapped_column(Numeric(6, 1))
    fuel_end: Mapped[float | None] = mapped_column(Numeric(6, 1))
    vehicle_photo_key: Mapped[str | None] = mapped_column(String(255))
    last_lat: Mapped[float | None] = mapped_column(Float)
    last_lng: Mapped[float | None] = mapped_column(Float)
    last_location_at: Mapped[datetime | None] = mapped_column(DateTime)
    driver: Mapped[User] = relationship(foreign_keys=[driver_id])
    vehicle: Mapped[Vehicle] = relationship()


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("district_id", "name_key", name="uq_customers_district_name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    fixed_no: Mapped[str] = mapped_column(String(20), unique=True)  # doimiy raqam, masalan A-0101
    # STIR Excel'da yo'q — keyin yuridik bo'lim to'ldiradi; kiritilsa takrorlanmaydi
    stir: Mapped[str | None] = mapped_column(String(9), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    name_key: Mapped[str] = mapped_column(String(200))  # birlashtirish uchun normallashtirilgan nom
    activity_type: Mapped[str | None] = mapped_column(String(100))
    director: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(30))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    address: Mapped[str | None] = mapped_column(String(255))
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    location_status: Mapped[LocationStatus] = mapped_column(enum_col(LocationStatus), default=LocationStatus.none, server_default="none")
    source: Mapped[str] = mapped_column(String(10), default="manual", server_default="manual")
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"))
    district: Mapped[District] = relationship()
    contacts: Mapped[list["CustomerContact"]] = relationship(order_by="CustomerContact.id", cascade="all, delete-orphan")
    contracts: Mapped[list["Contract"]] = relationship(order_by="Contract.id", viewonly=True)

    def active_contract(self, today: date | None = None) -> "Contract | None":
        """Bugun amal qiladigan shartnoma (contracts oldindan yuklangan bo'lishi kerak)."""
        today = today or date.today()
        return next((c for c in reversed(self.contracts) if c.is_active and c.valid_from <= today <= c.valid_to), None)

    @property
    def missing_fields(self) -> list[str]:
        """Haydovchi biriktirish uchun yetishmayotgan ma'lumotlar: 'stir', 'contract'."""
        return [f for f, ok in (("stir", bool(self.stir)), ("contract", self.active_contract() is not None)) if not ok]


class CustomerContact(TimestampMixin, Base):
    __tablename__ = "customer_contacts"
    __table_args__ = (UniqueConstraint("customer_id", "phone", name="uq_customer_contacts_phone"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    name: Mapped[str | None] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(30))


class ImportBatch(TimestampMixin, Base):
    __tablename__ = "import_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255))
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    customers_created: Mapped[int] = mapped_column(Integer, default=0)
    customers_merged: Mapped[int] = mapped_column(Integer, default=0)
    rows_skipped: Mapped[int] = mapped_column(Integer, default=0)
    report: Mapped[str | None] = mapped_column(Text)  # JSON: xatolar ro'yxati


class Contract(TimestampMixin, Base):
    __tablename__ = "contracts"
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    number: Mapped[str] = mapped_column(String(40), unique=True)
    signed_on: Mapped[date | None] = mapped_column(Date)
    type: Mapped[ContractType] = mapped_column(enum_col(ContractType))
    price: Mapped[float | None] = mapped_column(Numeric(14, 2))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date] = mapped_column(Date)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Request(TimestampMixin, Base):
    __tablename__ = "requests"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str | None] = mapped_column(String(20), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    contract_id: Mapped[int | None] = mapped_column(ForeignKey("contracts.id"))
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    status: Mapped[RequestStatus] = mapped_column(enum_col(RequestStatus), default=RequestStatus.new, index=True)
    waste_type: Mapped[WasteType] = mapped_column(enum_col(WasteType), default=WasteType.household)
    volume_estimate: Mapped[float | None] = mapped_column(Numeric(8, 2))
    preferred_time: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    driver_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    shift_id: Mapped[int | None] = mapped_column(ForeignKey("shifts.id"), index=True)
    naryad_no: Mapped[str | None] = mapped_column(String(30), unique=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    fail_reason: Mapped[FailReason | None] = mapped_column(enum_col(FailReason))
    fail_note: Mapped[str | None] = mapped_column(Text)
    # Call-center: kim qo'ng'iroq qildi, qayerdan keldi, 72 soatlik muddat, takroriy ariza
    source: Mapped[RequestSource] = mapped_column(enum_col(RequestSource), default=RequestSource.phone, server_default="phone")
    caller_name: Mapped[str | None] = mapped_column(String(150))
    caller_phone: Mapped[str | None] = mapped_column(String(30))
    due_at: Mapped[datetime | None] = mapped_column(DateTime, index=True)
    is_repeat: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    repeat_of_id: Mapped[int | None] = mapped_column(ForeignKey("requests.id"))
    overdue_notified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    cancel_reason: Mapped[str | None] = mapped_column(String(500))

    @property
    def overdue(self) -> bool:
        """Normativ muddat (72 soat) o'tgan va hali bajarilmagan."""
        from app.db.base import utcnow
        from app.models.enums import OPEN_STATUSES
        return bool(self.due_at) and self.status.value in OPEN_STATUSES and utcnow() > self.due_at

    customer: Mapped[Customer] = relationship()
    contract: Mapped[Contract | None] = relationship()
    shift: Mapped[Shift | None] = relationship()


class Appeal(TimestampMixin, Base):
    """Birinchi murojaat: bazada yo'q korxona qo'ng'iroq qildi — yuridik bo'lim karta va shartnoma ochadi."""
    __tablename__ = "appeals"
    id: Mapped[int] = mapped_column(primary_key=True)
    number: Mapped[str | None] = mapped_column(String(20), unique=True)
    status: Mapped[AppealStatus] = mapped_column(enum_col(AppealStatus), default=AppealStatus.new, index=True)
    district_id: Mapped[int] = mapped_column(ForeignKey("districts.id"), index=True)
    org_name: Mapped[str] = mapped_column(String(200))
    stir: Mapped[str | None] = mapped_column(String(9))
    address: Mapped[str | None] = mapped_column(String(255))
    activity_type: Mapped[str | None] = mapped_column(String(100))
    caller_name: Mapped[str | None] = mapped_column(String(150))
    caller_phone: Mapped[str | None] = mapped_column(String(30))
    source: Mapped[RequestSource] = mapped_column(enum_col(RequestSource), default=RequestSource.phone)
    waste_type: Mapped[WasteType] = mapped_column(enum_col(WasteType), default=WasteType.household)
    volume_estimate: Mapped[float | None] = mapped_column(Numeric(8, 2))
    preferred_time: Mapped[str | None] = mapped_column(String(50))
    note: Mapped[str | None] = mapped_column(Text)
    created_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    reject_reason: Mapped[str | None] = mapped_column(String(500))
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    request_id: Mapped[int | None] = mapped_column(ForeignKey("requests.id"))


class ChatMessage(TimestampMixin, Base):
    """Ariza yoki murojaat ichidagi yozishma: matn yoki ovozli xabar (audio 90 kun saqlanadi)."""
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_thread", "thread_type", "thread_id", "id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    thread_type: Mapped[str] = mapped_column(String(10))  # "request" | "appeal"
    thread_id: Mapped[int] = mapped_column(Integer)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(10), default="text")  # "text" | "voice"
    text: Mapped[str | None] = mapped_column(Text)
    file_key: Mapped[str | None] = mapped_column(String(200))
    content_type: Mapped[str | None] = mapped_column(String(50))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    expired: Mapped[bool] = mapped_column(Boolean, default=False, server_default=sa_false())
    author: Mapped["User"] = relationship(lazy="joined")


class ChatRead(Base):
    """Xodim yozishmani qayergacha o'qigani."""
    __tablename__ = "chat_reads"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    thread_type: Mapped[str] = mapped_column(String(10), primary_key=True)
    thread_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_read_id: Mapped[int] = mapped_column(Integer, default=0)


class NaryadCounter(Base):
    """Avtonaryad tartib raqami: har bir xizmat ko'rsatuvchi uchun har yili 1 dan."""
    __tablename__ = "naryad_counters"
    provider_id: Mapped[int] = mapped_column(ForeignKey("providers.id"), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, default=0)


class Act(Base):
    """Elektron dalolatnoma — haydovchi qo'lda kiritadigan va GPS natijasi."""
    __tablename__ = "acts"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), unique=True)
    containers: Mapped[int] = mapped_column(Integer)
    volume_m3: Mapped[float] = mapped_column(Numeric(8, 2))
    note: Mapped[str] = mapped_column(Text)
    lat: Mapped[float] = mapped_column(Float)
    lng: Mapped[float] = mapped_column(Float)
    distance_m: Mapped[int | None] = mapped_column(Integer)
    radius_m: Mapped[int] = mapped_column(Integer)
    in_radius: Mapped[bool | None] = mapped_column(Boolean)  # None — koordinatasiz korxona, radius tekshirilmadi
    vehicle_plate: Mapped[str] = mapped_column(String(20))
    completed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ActFile(TimestampMixin, Base):
    __tablename__ = "act_files"
    __table_args__ = (UniqueConstraint("request_id", "kind", name="uq_act_files_request_kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    kind: Mapped[FileKind] = mapped_column(enum_col(FileKind))
    storage_key: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(50))
    size_bytes: Mapped[int] = mapped_column(Integer)
    lat: Mapped[float | None] = mapped_column(Float)
    lng: Mapped[float | None] = mapped_column(Float)
    accuracy_m: Mapped[int | None] = mapped_column(Integer)  # rasm olingan paytdagi GPS aniqligi (planshet)
    uploaded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))


class RequestEvent(TimestampMixin, Base):
    __tablename__ = "request_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id"), index=True)
    status: Mapped[RequestStatus] = mapped_column(enum_col(RequestStatus))
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    note: Mapped[str | None] = mapped_column(String(255))


class RequestSeen(TimestampMixin, Base):
    """Xodim arizani ko'rganmi ("Yangi" belgisi har xodim uchun alohida)."""
    __tablename__ = "request_seen"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("requests.id", ondelete="CASCADE"), primary_key=True)


class AppSetting(Base):
    __tablename__ = "app_settings"
    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(255))


class SituationEvent(TimestampMixin, Base):
    """Vaziyat paneli: admin va manager ko'rishi kerak bo'lgan hodisalar (90 kun saqlanadi)."""
    __tablename__ = "situation_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    level: Mapped[SituationLevel] = mapped_column(enum_col(SituationLevel), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)  # frontend shu kalit bo'yicha tarjima qiladi
    message: Mapped[str] = mapped_column(String(500))          # o'zbekcha matn (log va zaxira uchun)
    params: Mapped[str | None] = mapped_column(Text)           # JSON: tarjima uchun qiymatlar
    district_id: Mapped[int | None] = mapped_column(ForeignKey("districts.id"), index=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    ref_type: Mapped[str | None] = mapped_column(String(20))   # request / customer / user / district / vehicle / import
    ref_id: Mapped[int | None] = mapped_column(Integer)


class SituationRead(Base):
    """Har bir xodim qaysi hodisagacha o'qigani."""
    __tablename__ = "situation_reads"
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    last_read_id: Mapped[int] = mapped_column(Integer, default=0)


__all__ = [
    "Base", "Region", "Provider", "District", "User", "Vehicle", "Shift", "Customer", "CustomerContact", "ImportBatch", "Contract",
    "Request", "NaryadCounter", "Act", "ActFile", "RequestEvent", "AppSetting", "SituationEvent", "SituationRead",
    "UserDistrict", "UserPermission", "Appeal", "RequestSeen", "ChatMessage", "ChatRead",
]
