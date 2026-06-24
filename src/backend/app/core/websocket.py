"""WebSocket connection manager with Redis pub/sub for cross-process broadcasting.

Provides per-workspace connection pools, JWT-based authentication via query
parameters, heartbeat health checks, and Redis pub/sub so that notifications
sent from any worker process reach all connected clients across all workers.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import WebSocket, WebSocketException, status

from app.config import settings
from app.core.security import decode_token

logger = logging.getLogger("amc.websocket")

# ── Redis channels ────────────────────────────────────────────────────────────

REDIS_CHANNEL_NOTIFICATIONS = "ws:notifications"
REDIS_CHANNEL_BROADCAST = "ws:broadcast"


class ConnectionManager:
    """Manages WebSocket connections with per-workspace and per-user pools.

    Features:
    - Per-workspace connection groups for workspace-scoped broadcasts.
    - Per-user connection tracking for user-scoped messages.
    - JWT authentication from WebSocket query parameters.
    - Heartbeat ping/pong for connection health.
    - Redis pub/sub listener for cross-process message delivery.

    Usage::

        manager = ConnectionManager()
        await manager.initialize()  # start the Redis listener

        @app.websocket("/ws")
        async def ws_endpoint(websocket: WebSocket):
            user = await manager.authenticate(websocket)
            await manager.connect(websocket, user_id, workspace_id)
            try:
                while True:
                    data = await websocket.receive_text()
                    ...
            finally:
                await manager.disconnect(websocket, workspace_id)
    """

    def __init__(self) -> None:
        # ── Connection pools ────────────────────────────────────────────
        # workspace_id -> set of WebSocket connections in that workspace
        self._workspace_connections: dict[str, set[WebSocket]] = {}
        # user_id -> set of WebSocket connections for that user
        self._user_connections: dict[str, set[WebSocket]] = {}
        # WebSocket -> user_id (reverse lookup)
        self._connection_owner: dict[int, str] = {}

        # ── Lock ────────────────────────────────────────────────────────
        self._lock = asyncio.Lock()

        # ── Redis ───────────────────────────────────────────────────────
        self._redis_pub: Any = None
        self._redis_sub: Any = None
        self._redis_task: asyncio.Task | None = None
        self._running = False

        # ── Heartbeat ───────────────────────────────────────────────────
        self._heartbeat_interval = 30  # seconds
        self._heartbeat_timeout = 10  # seconds
        self._heartbeat_task: asyncio.Task | None = None

    # ── Initialization / Teardown ──────────────────────────────────────────────

    async def initialize(self) -> None:
        """Start the Redis pub/sub listener and heartbeat monitor.

        Call once at application startup (inside the lifespan context).
        """
        self._running = True
        await self._init_redis()
        self._redis_task = asyncio.create_task(
            self._redis_listener(),
            name="ws-redis-listener",
        )
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
            name="ws-heartbeat",
        )
        logger.info("WebSocket ConnectionManager initialized")

    async def shutdown(self) -> None:
        """Gracefully shut down the Redis listener and heartbeat.

        Call at application shutdown.
        """
        self._running = False
        if self._redis_task:
            self._redis_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._redis_task
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._heartbeat_task
        if self._redis_pub:
            await self._redis_pub.close()
        if self._redis_sub:
            await self._redis_sub.close()
        logger.info("WebSocket ConnectionManager shut down")

    async def _init_redis(self) -> None:
        """Create Redis connections for pub/sub."""
        import redis.asyncio as aioredis

        self._redis_pub = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        self._redis_sub = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

    # ── Authentication ─────────────────────────────────────────────────────────

    async def authenticate(self, websocket: WebSocket) -> dict[str, Any]:
        """Validate the JWT token from WebSocket query parameters.

        Reads ``token`` from the query string, decodes it, and returns the
        token payload containing ``sub`` (user_id), ``tenant_id``, and
        ``workspace_id``.

        Raises:
            WebSocketException(401): If the token is missing or invalid.

        """
        token = websocket.query_params.get("token")
        if not token:
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Missing authentication token",
            )
        try:
            payload = decode_token(token)
        except Exception as exc:
            logger.warning("WebSocket auth failed: %s", exc)
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired token",
            ) from exc

        if payload.get("type") != "access":
            raise WebSocketException(
                code=status.WS_1008_POLICY_VIOLATION,
                reason="Only access tokens are accepted",
            )
        return payload

    # ── Connection Management ──────────────────────────────────────────────────

    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        workspace_id: str | None = None,
    ) -> None:
        """Accept a WebSocket and register it in the connection pools.

        Args:
            websocket: The WebSocket connection instance.
            user_id: The authenticated user's UUID string.
            workspace_id: Optional workspace UUID string for scoped broadcasts.

        """
        await websocket.accept()

        async with self._lock:
            # Track by user
            if user_id not in self._user_connections:
                self._user_connections[user_id] = set()
            self._user_connections[user_id].add(websocket)

            # Track by workspace
            ws_key = workspace_id or "_global"
            if ws_key not in self._workspace_connections:
                self._workspace_connections[ws_key] = set()
            self._workspace_connections[ws_key].add(websocket)

            # Reverse lookup
            self._connection_owner[id(websocket)] = user_id

        logger.debug(
            "WebSocket connected: user=%s workspace=%s active=%d",
            user_id,
            workspace_id,
            len(self._user_connections.get(user_id, set())),
        )

    async def disconnect(
        self,
        websocket: WebSocket,
        workspace_id: str | None = None,
    ) -> None:
        """Remove a WebSocket from all connection pools.

        Args:
            websocket: The WebSocket connection to remove.
            workspace_id: The workspace it was registered under.

        """
        async with self._lock:
            # Remove from user pool
            owner = self._connection_owner.pop(id(websocket), None)
            if owner and owner in self._user_connections:
                self._user_connections[owner].discard(websocket)
                if not self._user_connections[owner]:
                    del self._user_connections[owner]

            # Remove from workspace pool
            ws_key = workspace_id or "_global"
            if ws_key in self._workspace_connections:
                self._workspace_connections[ws_key].discard(websocket)
                if not self._workspace_connections[ws_key]:
                    del self._workspace_connections[ws_key]

        logger.debug(
            "WebSocket disconnected: user=%s workspace=%s",
            owner,
            workspace_id,
        )

    # ── Sending Messages ───────────────────────────────────────────────────────

    async def send_personal_message(
        self,
        user_id: str,
        message: dict[str, Any],
    ) -> int:
        """Send a JSON message to all connections for a specific user.

        Args:
            user_id: The target user's UUID string.
            message: A JSON-serializable dict.

        Returns:
            The number of connections the message was sent to.

        """
        return await self._broadcast_to_set(
            self._user_connections.get(user_id, set()),
            message,
        )

    async def broadcast_to_workspace(
        self,
        workspace_id: str,
        message: dict[str, Any],
    ) -> int:
        """Send a JSON message to all connections in a workspace.

        Args:
            workspace_id: The target workspace UUID string.
            message: A JSON-serializable dict.

        Returns:
            The number of connections the message was sent to.

        """
        return await self._broadcast_to_set(
            self._workspace_connections.get(workspace_id, set()),
            message,
        )

    async def broadcast_to_user(
        self,
        user_id: str,
        message: dict[str, Any],
    ) -> int:
        """Alias for :meth:`send_personal_message`."""
        return await self.send_personal_message(user_id, message)

    async def broadcast_global(self, message: dict[str, Any]) -> int:
        """Send a JSON message to **all** connected clients.

        Args:
            message: A JSON-serializable dict.

        Returns:
            The number of connections the message was sent to.

        """
        all_connections: set[WebSocket] = set()
        async with self._lock:
            for conns in self._user_connections.values():
                all_connections.update(conns)
        return await self._broadcast_to_set(all_connections, message)

    async def _broadcast_to_set(
        self,
        connections: set[WebSocket],
        message: dict[str, Any],
    ) -> int:
        """Send a JSON message to every WebSocket in *connections*.

        Stale connections are detected and cleaned up automatically.
        """
        if not connections:
            return 0

        payload = json.dumps(message, default=str)
        stale: list[WebSocket] = []
        count = 0

        for ws in connections:
            try:
                await ws.send_text(payload)
                count += 1
            except Exception:
                stale.append(ws)

        # Clean up stale connections
        if stale:
            async with self._lock:
                for ws in stale:
                    owner = self._connection_owner.pop(id(ws), None)
                    if owner and owner in self._user_connections:
                        self._user_connections[owner].discard(ws)
                    for pool in self._workspace_connections.values():
                        pool.discard(ws)

        return count

    # ── Redis Pub/Sub (Cross-Process) ──────────────────────────────────────────

    async def publish_notification(
        self,
        user_id: str,
        message: dict[str, Any],
        workspace_id: str | None = None,
    ) -> None:
        """Publish a notification to Redis for cross-process delivery.

        Every worker's Redis listener will pick this up and forward it to
        any locally-connected client matching *user_id*.

        Args:
            user_id: Target user UUID string.
            message: The notification message dict to deliver.
            workspace_id: Optional workspace scope.

        """
        envelope = {
            "type": "notification",
            "user_id": user_id,
            "workspace_id": workspace_id,
            "payload": message,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if self._redis_pub:
            await self._redis_pub.publish(
                REDIS_CHANNEL_NOTIFICATIONS,
                json.dumps(envelope, default=str),
            )

    async def publish_broadcast(
        self,
        message: dict[str, Any],
        workspace_id: str | None = None,
    ) -> None:
        """Publish a broadcast message to Redis for cross-process delivery.

        Args:
            message: The broadcast message dict.
            workspace_id: If set, only workers with connections in this
                          workspace will deliver the message.

        """
        envelope = {
            "type": "broadcast",
            "workspace_id": workspace_id,
            "payload": message,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        if self._redis_pub:
            await self._redis_pub.publish(
                REDIS_CHANNEL_BROADCAST,
                json.dumps(envelope, default=str),
            )

    async def _redis_listener(self) -> None:
        """Background task: listen on Redis pub/sub channels and dispatch
        messages to locally-connected clients.
        """
        try:
            pubsub = self._redis_sub.pubsub()
            await pubsub.subscribe(
                REDIS_CHANNEL_NOTIFICATIONS,
                REDIS_CHANNEL_BROADCAST,
            )
            logger.info(
                "Redis pub/sub listener started on channels: %s, %s",
                REDIS_CHANNEL_NOTIFICATIONS,
                REDIS_CHANNEL_BROADCAST,
            )

            async for message in pubsub.listen():
                if not self._running:
                    break
                if message["type"] != "message":
                    continue

                try:
                    data = json.loads(message["data"])
                except json.JSONDecodeError:
                    continue

                msg_type = data.get("type")
                if msg_type == "notification":
                    user_id = data.get("user_id")
                    payload = data.get("payload", {})
                    if user_id:
                        await self.send_personal_message(user_id, payload)

                elif msg_type == "broadcast":
                    workspace_id = data.get("workspace_id")
                    payload = data.get("payload", {})
                    if workspace_id:
                        await self.broadcast_to_workspace(workspace_id, payload)
                    else:
                        await self.broadcast_global(payload)

        except asyncio.CancelledError:
            logger.info("Redis pub/sub listener cancelled")
        except Exception:
            logger.exception("Redis pub/sub listener error")
        finally:
            with contextlib.suppress(Exception):
                await self._redis_sub.close()

    # ── Heartbeat ──────────────────────────────────────────────────────────────

    async def _heartbeat_loop(self) -> None:
        """Periodically send heartbeat pings to all connected clients.

        Clients are expected to respond with a ``heartbeat_ack`` message.
        Connections that fail are removed from the pools.
        """
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)

            ping = {
                "type": "heartbeat",
                "payload": {},
                "timestamp": datetime.now(UTC).isoformat(),
            }
            # Shallow-copy the current connections under the lock
            async with self._lock:
                all_conns = {ws for conns in self._user_connections.values() for ws in conns}

            stale: list[WebSocket] = []
            for ws in all_conns:
                try:
                    await ws.send_json(ping)
                except Exception:
                    stale.append(ws)

            if stale:
                logger.warning(
                    "Heartbeat: removing %d stale connection(s)",
                    len(stale),
                )
                async with self._lock:
                    for ws in stale:
                        owner = self._connection_owner.pop(id(ws), None)
                        if owner and owner in self._user_connections:
                            self._user_connections[owner].discard(ws)
                        for pool in self._workspace_connections.values():
                            pool.discard(ws)

    # ── Stats / Introspection ──────────────────────────────────────────────────

    @property
    def active_connections(self) -> int:
        """Return the total number of active WebSocket connections."""
        return len(self._connection_owner)

    @property
    def active_users(self) -> int:
        """Return the number of distinct connected users."""
        return len(self._user_connections)

    @property
    def active_workspaces(self) -> int:
        """Return the number of workspaces with active connections."""
        return len(self._workspace_connections)

    async def get_user_connections(self, user_id: str) -> int:
        """Return the number of active connections for a given user."""
        return len(self._user_connections.get(user_id, set()))

    async def get_workspace_connections(self, workspace_id: str) -> int:
        """Return the number of active connections in a given workspace."""
        return len(self._workspace_connections.get(workspace_id, set()))


# ── Global singleton ──────────────────────────────────────────────────────────

connection_manager = ConnectionManager()
"""Application-wide WebSocket ConnectionManager singleton."""
