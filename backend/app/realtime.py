"""Socket.IO server: jonli yangilanishlar.

Xonalar:
  managers          — admin va manager
  gps:{district_id} — shu tuman GPS xodimlari
  gps:all           — tumani belgilanmagan GPS xodimlari
  driver:{user_id}  — haydovchining o'zi
  user:{user_id}    — har bir xodimning shaxsiy xonasi (yozishma xabarlari faqat ko'rish huquqi borlarga)
"""
from http.cookies import SimpleCookie

import socketio

from app.core.config import get_settings
from app.core.security import ACCESS, decode_token

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=get_settings().cors_list)


@sio.event
async def connect(sid, environ, auth):
    token = (auth or {}).get("token")
    if not token:
        cookie = SimpleCookie(environ.get("HTTP_COOKIE", ""))
        token = cookie["access_token"].value if "access_token" in cookie else None
    data = decode_token(token, ACCESS) if token else None
    if not data:
        return False  # ulanish rad etiladi
    role, uid = data["role"], data["sub"]
    await sio.enter_room(sid, f"user:{uid}")
    if role in ("admin", "manager"):
        await sio.enter_room(sid, "managers")
    if role == "admin":
        await sio.enter_room(sid, "admins")  # Vaziyat paneli
    elif role == "gps":
        district = (auth or {}).get("district_id")
        await sio.enter_room(sid, f"gps:{district}" if district else "gps:all")
    elif role == "driver":
        await sio.enter_room(sid, f"driver:{uid}")
    elif role == "operator":
        await sio.enter_room(sid, "operators")  # o'zi ochgan arizalar holati jonli
    elif role == "legal":
        await sio.enter_room(sid, "legal")      # yangi murojaatlar navbati
    return True


async def emit_request_updated(payload: dict) -> None:
    rooms = ["managers", "operators", "legal", "gps:all", f"gps:{payload['district_id']}"]
    if payload.get("driver_id"):
        rooms.append(f"driver:{payload['driver_id']}")
    await sio.emit("request:updated", payload, room=rooms)


async def emit_driver_location(payload: dict) -> None:
    await sio.emit("driver:location", payload, room=["managers", "gps:all", f"gps:{payload['district_id']}"])


async def emit_situation(payload: dict) -> None:
    """Vaziyat paneli: faqat admin."""
    await sio.emit("situation:new", payload, room="admins")


async def emit_appeal_updated(payload: dict) -> None:
    """Murojaat yaratildi/ko'rib chiqildi: yuridik bo'lim navbati va operator ekrani."""
    await sio.emit("appeal:updated", payload, room=["legal", "operators", "managers"])


async def emit_chat_message(payload: dict, user_ids: list[int]) -> None:
    """Yangi yozishma xabari: faqat shu yozishmani ko'ra oladigan xodimlarga."""
    if user_ids:
        await sio.emit("chat:message", jsonable(payload), room=[f"user:{u}" for u in user_ids])


def jsonable(d: dict) -> dict:
    from fastapi.encoders import jsonable_encoder
    return jsonable_encoder(d)
