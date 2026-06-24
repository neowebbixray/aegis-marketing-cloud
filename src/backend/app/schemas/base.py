"""Unified response envelope and RFC 7807 error handling for the API.

Docs mandate:
- **Success** list endpoint envelopes: ``{data: [...], meta: {page, per_page, total, has_more}, links: {self, next, prev}}``
- **Success** single resource: ``{data: {...}}``
- **Error** envelopes (RFC 7807): ``{error: {type, title, status, detail, instance, trace_id, errors: [...]}}``
"""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

T = TypeVar("T")
DataT = TypeVar("DataT")


# ── Success Envelope ─────────────────────────────────────────────────────────


class PaginationMeta(BaseModel):
    """Pagination metadata per the docs spec."""

    page: int = 1
    per_page: int = 50
    total: int = 0
    has_more: bool = False


class PaginationLinks(BaseModel):
    """Link URLs for navigating paginated resources."""

    self: str | None = None
    next: str | None = None
    prev: str | None = None


class ListEnvelope(BaseModel, Generic[T]):
    """Unified list response: ``{data: [...], meta: {...}, links: {...}}``."""

    data: list[T]
    meta: PaginationMeta = PaginationMeta()
    links: PaginationLinks = PaginationLinks()


class SingleEnvelope(BaseModel, Generic[DataT]):
    """Unified single-resource response: ``{data: {...}}``."""

    data: DataT


# ── Field-Level Error ────────────────────────────────────────────────────────


class FieldError(BaseModel):
    """A single field-level validation error."""

    field: str
    message: str
    code: str = "invalid"


# ── RFC 7807 Error Envelope ──────────────────────────────────────────────────


ERROR_TYPE_BASE = "https://api.amc.io/errors"


# Maps HTTP status -> machine-readable error type path
ERROR_TYPE_PATHS: dict[int, str] = {
    400: "bad-request",
    401: "authentication-error",
    403: "authorization-error",
    404: "not-found",
    409: "conflict",
    422: "validation-error",
    429: "rate-limit-error",
    500: "internal-error",
    503: "service-unavailable",
}


class ErrorDetail(BaseModel):
    """An RFC 7807 Problem Detail wrapped in ``{error: ...}`` per AMC docs."""

    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    trace_id: str | None = None
    errors: list[FieldError] | None = None


class ErrorEnvelope(BaseModel):
    """Top-level error envelope: ``{error: {...}}``."""

    error: ErrorDetail


def build_problem_response(
    status_code: int,
    title: str,
    detail: str,
    request: Request | None = None,
    field_errors: list[FieldError] | None = None,
    trace_id: str | None = None,
) -> JSONResponse:
    """Build an RFC 7807 Problem Details JSON response.

    The response body follows the AMC docs spec:

    .. code-block:: json

        {
          "error": {
            "type": "https://api.amc.io/errors/validation-error",
            "title": "Validation Error",
            "status": 422,
            "detail": "The request body contains invalid fields.",
            "instance": "/api/v1/crm/contacts",
            "trace_id": "abc123def456",
            "errors": [
              {"field": "email", "message": "...", "code": "invalid_email"}
            ]
          }
        }
    """
    type_path = ERROR_TYPE_PATHS.get(status_code, "internal-error")
    body = ErrorEnvelope(
        error=ErrorDetail(
            type=f"{ERROR_TYPE_BASE}/{type_path}",
            title=title,
            status=status_code,
            detail=detail,
            instance=str(request.url) if request else None,
            trace_id=trace_id or uuid4().hex[:12],
            errors=field_errors,
        ),
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(exclude_none=True),
        headers={"X-Request-ID": body.error.trace_id or ""} if body.error.trace_id else {},
    )


def build_list_response(
    data: list[BaseModel] | list[dict],
    total: int,
    page: int,
    per_page: int,
    request: Request | None = None,
) -> dict:
    """Build a ``{data, meta, links}`` envelope for list endpoints."""
    has_more = (page * per_page) < total
    base_path = str(request.url.remove_query_params(("page", "cursor"))) if request else ""

    def _page_link(p: int) -> str | None:
        if not base_path:
            return None
        sep = "&" if "?" in base_path else "?"
        return f"{base_path}{sep}page={p}&per_page={per_page}"

    return {
        "data": [item.model_dump() if isinstance(item, BaseModel) else item for item in data],
        "meta": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "has_more": has_more,
        },
        "links": {
            "self": _page_link(page),
            "next": _page_link(page + 1) if has_more else None,
            "prev": _page_link(page - 1) if page > 1 else None,
        },
    }


def build_single_response(data: BaseModel | dict) -> dict:
    """Build a ``{data: {...}}`` envelope for single-resource endpoints."""
    return {"data": data.model_dump() if isinstance(data, BaseModel) else data}
