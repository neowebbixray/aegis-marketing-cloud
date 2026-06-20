"""
GraphQL schema for Aegis Marketing Cloud.
"""

from __future__ import annotations

import strawberry
from fastapi import APIRouter
from strawberry.fastapi import GraphQLRouter


@strawberry.type
class Query:
    """Root GraphQL query."""

    @strawberry.field
    def health(self) -> str:
        return "OK"


@strawberry.type
class Mutation:
    """Root GraphQL mutation."""

    @strawberry.field
    def ping(self) -> str:
        return "pong"


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_router = GraphQLRouter(schema, prefix="/api/v1/graphql")
