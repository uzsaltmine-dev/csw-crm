"""Ruxsatlar katalogi va rol andozalari.

Ruxsat kodi: "<bo'lim>.<amal>". Admin hammasiga ega (bazaga yozilmaydi). Boshqa xodimlarga ruxsat alohida yoziladi:
yangi xodim yaratilganda rolining andozasi qo'llanadi, keyin admin (yoki o'z xodimlari uchun manager) ochadi/yopadi.
Faqat admin: tumanlar, umumiy sozlamalar, Vaziyat paneli, xodimni tasdiqlash.
"""
from app.models.enums import Role

# bo'lim → amallar (frontend jadvali shu tartibda chiziladi)
MODULES: dict[str, list[str]] = {
    "customers": ["view", "create", "edit", "contract", "location_confirm", "import"],
    "staff": ["view", "create", "edit", "deactivate", "reset_password", "permissions"],
    "vehicles": ["view", "create", "edit", "deactivate"],
    "settings": ["view", "radius_edit"],
    "requests": ["view", "create", "cancel"],
    "appeals": ["view", "create", "review"],
    "stats": ["view"],
}
ALL_CODES: frozenset[str] = frozenset(f"{m}.{a}" for m, actions in MODULES.items() for a in actions)

# Hozirgi xatti-harakatni saqlaydigan andozalar (migratsiya mavjud xodimlarni shu bilan to'ldiradi)
ROLE_TEMPLATES: dict[Role, list[str]] = {
    Role.admin: [],
    Role.manager: ["customers.view", "customers.location_confirm", "staff.view", "vehicles.view", "settings.view",
                   "requests.view", "stats.view"],
    Role.legal: ["customers.view", "customers.create", "customers.edit", "customers.contract", "appeals.view", "appeals.review"],
    Role.gps: ["customers.view", "requests.view"],
    Role.operator: ["customers.view", "requests.view", "requests.create", "appeals.view", "appeals.create"],
    Role.driver: [],
}

# Manager o'z doirasida boshqara oladigan rollar ("o'z xodimlari")
STAFF_ROLES: frozenset[Role] = frozenset({Role.gps, Role.legal, Role.operator, Role.driver})
# Bitta tumanga bog'lanadigan rollar (users.district_id); qolganlari user_districts orqali bir nechta tumanga
SINGLE_DISTRICT_ROLES: frozenset[Role] = frozenset({Role.gps, Role.driver})
MULTI_DISTRICT_ROLES: frozenset[Role] = frozenset({Role.manager, Role.legal, Role.operator})


def template(role: Role) -> list[str]:
    return list(ROLE_TEMPLATES.get(role, []))


def apply_template(user, district_ids: list[int] | None = None) -> None:
    """Seed va testlar uchun: rol andozasi va (manager/yurist/operator uchun) tumanlar."""
    from app.models import UserDistrict, UserPermission
    user.perm_rows = [UserPermission(code=c) for c in template(user.role)]
    if district_ids is not None and user.role in MULTI_DISTRICT_ROLES:
        user.district_rows = [UserDistrict(district_id=d) for d in district_ids]
