from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Biznes qoidasi buzilganda tashlanadi.

    `code` — frontend tarjima uchun ishlatadigan barqaror kalit,
    `message` — o'zbek tilidagi tushuntirish (log va Postman uchun).
    """

    def __init__(self, status: int, code: str, message: str, details: dict | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def not_found(what: str) -> AppError:
    return AppError(404, f"{what}_not_found", f"{what} topilmadi")


def forbidden(message: str = "Bu amal uchun ruxsat yo'q") -> AppError:
    return AppError(403, "forbidden", message)


def conflict(code: str, message: str) -> AppError:
    return AppError(409, code, message)


def invalid(code: str, message: str) -> AppError:
    return AppError(422, code, message)


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    err = {"code": exc.code, "message": exc.message}
    if exc.details:
        err["details"] = exc.details
    return JSONResponse(status_code=exc.status, content={"error": err})
