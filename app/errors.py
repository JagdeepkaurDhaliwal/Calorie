from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AppError(Exception):
    http_status = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, details: list | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or []


class BadRequest(AppError):
    http_status = 400
    code = "BAD_REQUEST"


class Unauthorized(AppError):
    http_status = 401
    code = "UNAUTHORIZED"


class Forbidden(AppError):
    http_status = 403
    code = "FORBIDDEN"


class NotFound(AppError):
    http_status = 404
    code = "NOT_FOUND"


class Conflict(AppError):
    http_status = 409
    code = "CONFLICT"


class ValidationError(AppError):
    http_status = 422
    code = "VALIDATION_ERROR"


def error_body(code: str, message: str, details: list | None = None) -> dict:
    return {"error": {"code": code, "message": message, "details": details or []}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content=error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        details = []
        for err in exc.errors():
            loc = err.get("loc", [])
            field = ".".join(str(x) for x in loc if x != "body")
            details.append({"field": field or "body", "issue": err.get("msg", "invalid")})
        return JSONResponse(
            status_code=422,
            content=error_body("VALIDATION_ERROR", "Request validation failed", details),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, AppError):
            raise exc
        return JSONResponse(
            status_code=500,
            content=error_body("INTERNAL_ERROR", "An unexpected error occurred"),
        )
