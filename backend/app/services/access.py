"""Tuman doirasi va "o'z xodimlari" qoidalari (manager uchun). Admin — cheklovsiz."""
from app.core.errors import forbidden
from app.core.permissions import STAFF_ROLES
from app.models import User
from app.models.enums import Role


def is_admin(user: User) -> bool:
    return user.role == Role.admin


def scope(user: User) -> set[int] | None:
    """Ko'rish/o'zgartirish mumkin bo'lgan tumanlar; None — hammasi (admin)."""
    return None if is_admin(user) else set(user.district_ids)


def in_scope(user: User, district_id: int | None) -> bool:
    s = scope(user)
    return s is None or (district_id is not None and district_id in s)


def check_scope(user: User, district_id: int | None) -> None:
    if not in_scope(user, district_id):
        raise forbidden("Bu tuman sizning doirangizda emas")


def is_own_staff(actor: User, target: User) -> bool:
    """Manager uchun "o'z xodimi": GPS/yurist/operator/haydovchi, barcha tumanlari manager doirasida."""
    if is_admin(actor):
        return True
    s = scope(actor) or set()
    ids = set(target.district_ids)
    return target.role in STAFF_ROLES and bool(ids) and ids <= s


def check_own_staff(actor: User, target: User) -> None:
    if not is_own_staff(actor, target):
        raise forbidden("Bu xodim sizning doirangizda emas")
