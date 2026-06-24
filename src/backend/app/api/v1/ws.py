"""WebSocket endpoint for real-time notifications and events.

Supports:
- JWT token authentication via ``?token=`` query parameter.
- Multiple message types: ``notification``, ``event``, ``heartbeat``,
  ``typing``, ``status_update``.
- Per-workspace connection management via ``ConnectionManager``.
- Redis pub/sub for cross-worker message delivery.

The endpoint re-uses the existing FastAPI dependency machinery to validate
the JWT, extract the user, and resolve the tenant/workspace context.

Usage (client side)::

    const ws = new WebSocket("wss://api.amc.io/api/v1/ws?token=<jwt>");
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        console.log(msg.type, msg.payload);
    };
    // Respond to heartbeat pings
    ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        if (msg.type === "heartbeat") {
            ws.send(JSON.stringify({type: "heartbeat_ack", payload: {}}));
        }
    };
"""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.websocket import ConnectionManager, connection_manager
from app.schemas.notifications import (
    WebSocketMessage,
    WebSocketMessageType,
)

logger = logging.getLogger("amc.api.ws")

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """Main WebSocket endpoint at ``/api/v1/ws``.

    Authentication is handled via JWT token in the query string
    (``?token=<access_token>``).

    Message flow:
    - Server sends ``heartbeat`` pings periodically.
    - Client responds with ``heartbeat_ack``.
    - Server pushes ``notification`` messages as they arrive.
    - The client may send ``typing``, ``status_update``, or other
      messages to broadcast to the workspace.
    """
    manager = connection_manager

    # ── Authenticate ──────────────────────────────────────────────────────
    try:
        payload = await manager.authenticate(websocket)
    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    user_id: str = payload.get("sub", "")
    tenant_id: str | None = payload.get("tenant_id")
    workspace_id: str | None = payload.get("workspace_id")

    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    # ── Connect ──────────────────────────────────────────────────────────
    await manager.connect(websocket, user_id, workspace_id)

    # Send a welcome / connected message
    with contextlib.suppress(Exception):
        await _send_message(
            websocket,
            WebSocketMessageType.CONNECTED,
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "active_connections": await manager.get_user_connections(user_id),
            },
        )

    logger.info(
        "WebSocket client connected: user=%s tenant=%s workspace=%s",
        user_id,
        tenant_id,
        workspace_id,
    )

    # ── Message loop ─────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _send_error(websocket, "Invalid JSON")
                continue

            msg_type = data.get("type", "")
            data.get("payload", {})

            if msg_type == "heartbeat_ack":
                # Client responded to our heartbeat — nothing to do
                continue

            if msg_type == "heartbeat":
                # Client-initiated heartbeat (request a pong)
                await _send_message(
                    websocket,
                    WebSocketMessageType.HEARTBEAT_ACK,
                    {"timestamp": datetime.now(UTC).isoformat()},
                )

            elif msg_type == "typing":
                # Relay typing indicator to workspace
                await _handle_typing(manager, websocket, data, user_id, workspace_id)

            elif msg_type == "status_update":
                # Broadcast status change to workspace
                await _handle_status_update(
                    manager,
                    data,
                    user_id,
                    workspace_id,
                )

            elif msg_type == "ping":
                # Simple ping/pong
                await _send_message(
                    websocket,
                    WebSocketMessageType.HEARTBEAT_ACK,
                    {"pong": True},
                )

            else:
                logger.debug(
                    "Unknown WebSocket message type: %s from user=%s",
                    msg_type,
                    user_id,
                )
                await _send_error(
                    websocket,
                    f"Unknown message type: {msg_type}",
                )

    except WebSocketDisconnect:
        logger.info(
            "WebSocket client disconnected: user=%s workspace=%s",
            user_id,
            workspace_id,
        )
    except Exception:
        logger.exception(
            "WebSocket error for user=%s workspace=%s",
            user_id,
            workspace_id,
        )
    finally:
        await manager.disconnect(websocket, workspace_id)


# ── Internal helpers ──────────────────────────────────────────────────────────


async def _send_message(
    websocket: WebSocket,
    msg_type: WebSocketMessageType | str,
    payload: dict[str, Any],
    notification_id: str | None = None,
) -> None:
    """Send a JSON-encoded WebSocket message to a single client."""
    msg = WebSocketMessage(
        type=msg_type
        if isinstance(msg_type, WebSocketMessageType)
        else WebSocketMessageType(msg_type),
        payload=payload,
        timestamp=datetime.now(UTC).isoformat(),
        notification_id=notification_id,
    )
    await websocket.send_text(msg.model_dump_json())


async def _send_error(websocket: WebSocket, detail: str) -> None:
    """Send an error message to a WebSocket client."""
    await _send_message(
        websocket,
        WebSocketMessageType.ERROR,
        {"detail": detail},
    )


async def _handle_typing(
    manager: ConnectionManager,
    websocket: WebSocket,
    data: dict[str, Any],
    user_id: str,
    workspace_id: str | None,
) -> None:
    """Relay a ``typing`` indicator to the workspace."""
    typing_msg = {
        "type": "typing",
        "payload": {
            "user_id": user_id,
            "is_typing": data.get("payload", {}).get("is_typing", True),
            "thread_id": data.get("payload", {}).get("thread_id"),
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if workspace_id:
        await manager.broadcast_to_workspace(workspace_id, typing_msg)
    else:
        await manager.broadcast_global(typing_msg)


async def _handle_status_update(
    manager: ConnectionManager,
    data: dict[str, Any],
    user_id: str,
    workspace_id: str | None,
) -> None:
    """Broadcast a user status change to the workspace."""
    status_msg = {
        "type": "status_update",
        "payload": {
            "user_id": user_id,
            "status": data.get("payload", {}).get("status", "online"),
            "status_message": data.get("payload", {}).get("status_message"),
        },
        "timestamp": datetime.now(UTC).isoformat(),
    }
    if workspace_id:
        await manager.broadcast_to_workspace(workspace_id, status_msg)
    else:
        await manager.broadcast_global(status_msg)
