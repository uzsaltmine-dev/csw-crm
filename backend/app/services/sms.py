"""SMS: Eskiz.uz adapteri. ESKIZ_EMAIL/ESKIZ_PASSWORD sozlanmagan bo'lsa (demo, test) — yuborilmaydi, faqat jurnalga yoziladi.

Eskiz API: POST /api/auth/login (email, password) → token; POST /api/message/sms/send (mobile_phone, message, from).
"""
import asyncio
import logging
import re

import httpx

from app.core.config import get_settings

log = logging.getLogger("csw.sms")
ESKIZ = "https://notify.eskiz.uz/api"
SENT: list[tuple[str, str]] = []  # demo/test: yuborilgan (yoki yuborilishi kerak bo'lgan) xabarlar
_token: str | None = None


def _msisdn(phone: str) -> str | None:
    d = re.sub(r"\D", "", phone or "")
    if len(d) == 9:
        d = "998" + d
    return d if len(d) == 12 and d.startswith("998") else None


async def _login(client: httpx.AsyncClient) -> str:
    s = get_settings()
    r = await client.post(f"{ESKIZ}/auth/login", data={"email": s.eskiz_email, "password": s.eskiz_password})
    r.raise_for_status()
    return r.json()["data"]["token"]


async def send(phone: str, text: str) -> bool:
    """Xatoda ilova to'xtamaydi — jurnalga yoziladi. True — provayder qabul qildi."""
    global _token
    to = _msisdn(phone)
    SENT.append((phone, text))
    s = get_settings()
    if not to:
        log.warning("sms: telefon noto'g'ri: %s", phone)
        return False
    if not (s.eskiz_email and s.eskiz_password):
        log.info("sms (demo, yuborilmadi) %s: %s", to[:5] + "****" + to[-3:], text)
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for _ in range(2):
                _token = _token or await _login(client)
                r = await client.post(f"{ESKIZ}/message/sms/send", headers={"Authorization": f"Bearer {_token}"},
                                      data={"mobile_phone": to, "message": text, "from": s.sms_sender})
                if r.status_code == 401:  # token eskirgan
                    _token = None
                    continue
                r.raise_for_status()
                return True
    except Exception:  # noqa: BLE001
        log.exception("sms yuborilmadi")
    return False


def send_later(phone: str, text: str) -> None:
    """Commit'dan keyin fon rejimida (javobni kutdirmaydi)."""
    asyncio.get_running_loop().create_task(send(phone, text))
