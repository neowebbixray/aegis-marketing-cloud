"""
Strawberry GraphQL schema for Aegis Marketing Cloud.

Per the docs design:
- REST is the system of record (CRUD operations)
- GraphQL is read-optimized (complex nested queries)
- GraphQL lives at ``/api/v1/graphql``
"""

from __future__ import annotations

import strawberry
from strawberry.fastapi import GraphQLRouter


# ── Scalar types ─────────────────────────────────────────────────────────────


@strawberry.type
class Contact:
    id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    company: str | None = None
    position: str | None = None
    lifecycle_stage: str | None = None
    source: str | None = None
    created_at: str
    updated_at: str


@strawberry.type
class Deal:
    id: str
    name: str
    value: float | None = None
    currency: str | None = None
    pipeline_stage_id: str | None = None
    contact_id: str | None = None
    organization_id: str | None = None
    owner_id: str | None = None
    probability: int | None = None
    expected_close_date: str | None = None
    created_at: str
    updated_at: str


@strawberry.type
class Pipeline:
    id: str
    name: str
    description: str | None = None
    is_default: bool = False
    created_at: str
    updated_at: str


# ── Query ────────────────────────────────────────────────────────────────────


@strawberry.type
class Query:
    @strawberry.field
    async def contacts(self, page: int = 1, limit: int = 50) -> list[Contact]:
        """List contacts (delegates to REST service layer via DB)."""
        # Auth context / tenant resolution happens via FastAPI dependency injection
        # This is a stub — full implementation delegates to ContactService
        return []

    @strawberry.field
    async def contact(self, id: str) -> Contact | None:
        """Get a single contact by ID."""
        return None

    @strawberry.field
    async def deals(self, page: int = 1, limit: int = 50) -> list[Deal]:
        """List deals."""
        return []

    @strawberry.field
    async def deal(self, id: str) -> Deal | None:
        """Get a single deal by ID."""
        return None

    @strawberry.field
    async def pipelines(self) -> list[Pipeline]:
        """List pipelines."""
        return []

    @strawberry.field
    async def pipeline(self, id: str) -> Pipeline | None:
        """Get a single pipeline by ID."""
        return None


# ── Mutation ─────────────────────────────────────────────────────────────────


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def health_check(self) -> str:
        """Simple health check mutation."""
        return "GraphQL is operational"


# ── Schema & Router ──────────────────────────────────────────────────────────

schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, prefix="/api/v1/graphql")
