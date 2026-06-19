"""Prometheus metrics definitions for Aegis Marketing Cloud.

Provides named counters, histograms, and gauges used by the metrics middleware
and throughout the application for observability.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# ── HTTP Metrics ──────────────────────────────────────────────────────────────
HTTP_REQUEST_COUNT = Counter(
    "http_request_count",
    "Total number of HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# ── Database Metrics ──────────────────────────────────────────────────────────
DB_CONNECTION_ACTIVE = Gauge(
    "db_connection_active",
    "Current number of active database connections (pool size + overflow)",
)

# ── AI / ML Metrics ───────────────────────────────────────────────────────────
AI_INFERENCE_DURATION = Histogram(
    "ai_inference_duration_seconds",
    "AI inference duration in seconds",
    labelnames=["agent_id"],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

# ── Rate Limiting Metrics ─────────────────────────────────────────────────────
RATE_LIMIT_BLOCKED = Counter(
    "rate_limit_blocked_total",
    "Total number of requests blocked by rate limiting",
    labelnames=["tenant_tier"],
)

# ── WebSocket Metrics ─────────────────────────────────────────────────────────
ACTIVE_WS_CONNECTIONS = Gauge(
    "active_ws_connections",
    "Current number of active WebSocket connections",
)
