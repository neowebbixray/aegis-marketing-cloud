"""
Custom exception classes and FastAPI exception handlers following
the AMC docs RFC 7807 specification.

Docs spec says error format:
``{error: {type, title, status, detail, instance, trace_id, errors: [...]}}``
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.schemas.base import FieldError, build_problem_response


# ── Exception classes ────────────────────────────────────────────────────────
class AppException(Exception):
    """Base application exception with optional detail and extra data."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    title: str = "Internal Server Error"
    detail: str = "An unexpected error occurred."
    extra: Optional[dict[str, Any]] = None

    def __init__(
        self,
        detail: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if detail is not None:
            self.detail = detail
        self.extra = extra
        super().__init__(self.detail)


class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    title = "Resource Not Found"


class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    title = "Authentication Error"


class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    title = "Authorization Error"


class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    title = "Conflict"


class ValidationException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    title = "Validation Error"


class RateLimitExceeded(AppException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    title = "Rate Limit Exceeded"


# ── FastAPI exception handlers (RFC 7807) ───────────────────────────────────


def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Convert an AppException to the docs-specified RFC 7807 error envelope."""
    return build_problem_response(
        status_code=exc.status_code,
        title=exc.title,
        detail=exc.detail,
        request=request,
    )


def _pydantic_validation_handler(
    request: Request,
    exc: PydanticValidationError,
) -> JSONResponse:
    """Convert Pydantic ``ValidationError`` to the docs-specified field-error format."""
    field_errors = []
    for err in exc.errors():
        field_errors.append(
            FieldError(
                field=".".join(str(loc) for loc in err.get("loc", [])),
                message=err.get("msg", "Validation error"),
                code=err.get("type", "invalid"),
            )
        )
    return build_problem_response(
        status_code=422,
        title="Validation Error",
        detail="The request body contains invalid fields.",
        request=request,
        field_errors=field_errors,
    )


def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all handler for unhandled exceptions."""
    return build_problem_response(
        status_code=500,
        title="Internal Server Error",
        detail="An unexpected error occurred.",
        request=request,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI *app*."""
    for exc_cls in (
        AppException,
        NotFoundException,
        UnauthorizedException,
        ForbiddenException,
        ConflictException,
        ValidationException,
        RateLimitExceeded,
    ):
        app.add_exception_handler(exc_cls, _app_exception_handler)

    # Also handle Pydantic validation errors and unhandled exceptions
    app.add_exception_handler(PydanticValidationError, _pydantic_validation_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
