import logging
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("csw.http")
SAFE = {"GET", "HEAD", "OPTIONS"}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Har so'rovga X-Request-ID beradi va davomiyligini log qiladi (Grafana/Loki uchun)."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        response = await call_next(request)
        ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = rid
        log.info("%s %s %s %.1fms rid=%s", request.method, request.url.path, response.status_code, ms, rid)
        return response


class CsrfHeaderMiddleware(BaseHTTPMiddleware):
    """Cookie orqali autentifikatsiyada CSRF himoyasi: o'zgartiruvchi so'rovlar
    `X-Requested-With: csw` sarlavhasini yuborishi shart (brauzer boshqa saytdan buni qo'sha olmaydi).
    Bearer token bilan kelgan so'rovlar (Postman) bundan ozod."""

    async def dispatch(self, request: Request, call_next):
        if (request.method not in SAFE and request.url.path.startswith("/api/")
                and not request.headers.get("authorization")
                and not (request.url.path.startswith("/api/v1/integrations/") and request.headers.get("x-api-key"))
                and request.headers.get("x-requested-with") != "csw"):
            return JSONResponse(status_code=403, content={"error": {"code": "csrf", "message": "X-Requested-With sarlavhasi yo'q"}})
        return await call_next(request)
