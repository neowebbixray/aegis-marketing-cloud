"""
Health check endpoints for Aegis Marketing Cloud.

Provides three tiers of health checking:
- ``/api/v1/health/live`` — Liveness probe (is the app running?)
- ``/api/v1/health/ready`` — Readiness probe (are dependencies reachable?)
- ``/api/v1/health`` — Full health report with per-service status, latency, versions
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastapi import APIRouter
from sqlalchemy import text as sa_text

from app.config import settings

logger = logging.getLogger("amc.health")

router = APIRouter(prefix="/health", tags=["system"])

# ── Helpers ──────────────────────────────────────────────────────────────────


async def _check_postgres() -> dict[str, Any]:
    """Check PostgreSQL connectivity via a simple SELECT 1."""
    from app.database import engine

    start = time.monotonic()
    result: dict[str, Any] = {
        "name": "postgres",
        "status": "unknown",
        "latency_ms": None,
        "error": None,
    }
    try:
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
        result["status"] = "connected"
    except Exception as exc:
        result["status"] = "disconnected"
        result["error"] = str(exc)
    result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return result


async def _check_redis() -> dict[str, Any]:
    """Check Redis connectivity via PING."""
    result: dict[str, Any] = {
        "name": "redis",
        "status": "unknown",
        "latency_ms": None,
        "error": None,
        "version": None,
    }
    start = time.monotonic()
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url, socket_connect_timeout=3)
        pong = await r.ping()
        if pong:
            result["status"] = "connected"
            try:
                info = await r.info("server")
                result["version"] = info.get("redis_version")
            except Exception:
                pass
        await r.aclose()
    except Exception as exc:
        result["status"] = "disconnected"
        result["error"] = str(exc)
    result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return result


async def _check_minio() -> dict[str, Any]:
    """Check MinIO/S3 connectivity (if configured)."""
    result: dict[str, Any] = {
        "name": "minio",
        "status": "unknown",
        "latency_ms": None,
        "error": None,
    }
    if not settings.minio_endpoint:
        result["status"] = "not_configured"
        return result

    start = time.monotonic()
    try:
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )
        # List buckets as a connectivity check
        list(client.list_buckets())
        result["status"] = "connected"
    except Exception as exc:
        result["status"] = "disconnected"
        result["error"] = str(exc)
    result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return result


async def _check_qdrant() -> dict[str, Any]:
    """Check Qdrant vector store connectivity."""
    result: dict[str, Any] = {
        "name": "qdrant",
        "status": "unknown",
        "latency_ms": None,
        "error": None,
        "version": None,
    }
    start = time.monotonic()
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            prefer_grpc=settings.qdrant_prefer_grpc,
            https=settings.qdrant_https,
        )
        collections = client.get_collections()
        result["status"] = "connected"
        result["version"] = getattr(collections, "time", None)
    except Exception as exc:
        result["status"] = "disconnected"
        result["error"] = str(exc)
    result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return result


async def _check_rabbitmq() -> dict[str, Any]:
    """Check RabbitMQ connectivity (if configured)."""
    result: dict[str, Any] = {
        "name": "rabbitmq",
        "status": "unknown",
        "latency_ms": None,
        "error": None,
    }
    if not settings.rabbitmq_url or "***" in settings.rabbitmq_url:
        result["status"] = "not_configured"
        result["error"] = "RABBITMQ_URL not properly configured"
        return result

    start = time.monotonic()
    try:
        import aio_pika

        connection = await asyncio.wait_for(
            aio_pika.connect_robust(settings.rabbitmq_url), timeout=5
        )
        await connection.close()
        result["status"] = "connected"
    except Exception as exc:
        result["status"] = "disconnected"
        result["error"] = str(exc)
    result["latency_ms"] = round((time.monotonic() - start) * 1000, 2)
    return result


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/live")
async def liveness() -> dict[str, Any]:
    """Liveness probe — simple check that the application process is running.

    Returns immediately with no dependency checks. Suitable for Kubernetes
    liveness probes.
    """
    return {
        "status": "alive",
        "app": settings.app_name,
    }


@router.get("/ready")
async def readiness() -> dict[str, Any]:
    """Readiness probe — check that critical dependencies are reachable.

    Returns HTTP 200 only if the database (PostgreSQL) is reachable.
    Suitable for Kubernetes readiness probes.
    """
    db = await _check_postgres()
    if db["status"] == "connected":
        return {
            "status": "ready",
            "app": settings.app_name,
            "database": "connected",
        }
    return {
        "status": "not_ready",
        "app": settings.app_name,
        "database": "disconnected",
        "error": db.get("error"),
    }


@router.get("")
async def full_health() -> dict[str, Any]:
    """Full health report — checks all configured services.

    Returns a structured report with per-service status, latency, and version
    info. The top-level ``status`` is ``healthy`` if all configured services
    are reachable, ``degraded`` if some are down, and ``unhealthy`` if the
    database itself is unreachable.
    """
    checks = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_minio(),
        _check_qdrant(),
        _check_rabbitmq(),
        return_exceptions=True,
    )

    services: list[dict[str, Any]] = []
    for check in checks:
        if isinstance(check, Exception):
            services.append({
                "name": "unknown",
                "status": "error",
                "error": str(check),
            })
        else:
            services.append(check)

    # Determine overall status
    db_status = next((s["status"] for s in services if s["name"] == "postgres"), "unknown")
    connected = sum(1 for s in services if s["status"] == "connected")
    total = sum(1 for s in services if s["status"] not in ("unknown", "not_configured"))

    if db_status != "connected":
        overall = "unhealthy"
    elif connected == total:
        overall = "healthy"
    elif connected > 0:
        overall = "degraded"
    else:
        overall = "unhealthy"

    return {
        "status": overall,
        "app": settings.app_name,
        "version": "0.1.0",
        "environment": settings.environment,
        "services": services,
    }


# ── Legacy health endpoint (compatibility) ──────────────────────────────────


@router.get("/legacy")
async def legacy_health() -> dict[str, Any]:
    """Simple health endpoint compatible with the original /health route."""
    from app.database import engine

    db_ok = True
    try:
        async with engine.connect() as conn:
            await conn.execute(sa_text("SELECT 1"))
    except Exception:
        db_ok = False

    return {
        "status": "healthy" if db_ok else "degraded",
        "app": settings.app_name,
        "version": "0.1.0",
        "database": "connected" if db_ok else "disconnected",
    }
