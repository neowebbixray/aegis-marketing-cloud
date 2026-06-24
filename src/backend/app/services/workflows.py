"""Workflow service — handles interactions with n8n workflow engine."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx


class N8nClient:
    """Client for interacting with n8n API."""

    def __init__(self, base_url: str, api_key: str | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if api_key:
            self.headers["X-N8N-API-KEY"] = api_key

    async def _request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient() as client:
            url = f"{self.base_url}{endpoint}"
            resp = await client.request(
                method,
                url,
                headers=self.headers,
                json=json_data,
                params=params,
                timeout=30.0,
            )
            resp.raise_for_status()
            return resp.json()

    async def get_workflows(self, limit: int = 100, offset: int = 0) -> dict[str, Any]:
        """List workflows."""
        return await self._request(
            "GET",
            "/api/v1/workflows",
            params={"limit": limit, "offset": offset},
        )

    async def get_workflow(self, workflow_id: str) -> dict[str, Any]:
        """Get a single workflow."""
        return await self._request("GET", f"/api/v1/workflows/{workflow_id}")

    async def trigger_workflow(self, workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        """Trigger a workflow by its ID."""
        # We'll use the execution endpoint to trigger the workflow.
        # This assumes the workflow is set up to be triggered via the API.
        return await self._request(
            "POST",
            f"/api/v1/workflows/{workflow_id}/execute",
            json_data={"workflowData": {"data": payload}},
        )


# Read environment variables for the n8n connection.
N8N_URL = os.getenv("N8N_URL", "http://n8n:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY")

# Create a singleton client for internal use.
n8n_client = N8nClient(base_url=N8N_URL, api_key=N8N_API_KEY)


async def trigger(workflow_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Trigger an n8n workflow."""
    return await n8n_client.trigger_workflow(workflow_id, payload)


async def process_reply(message_id: str) -> bool:
    """Process an incoming email reply and link to workflow.

    This is a placeholder for the actual implementation.
    In production, this function:
    1. Retrieves the original email by message_id
    2. Matches it to a workflow trigger
    3. Passes the reply content to the matched workflow
    4. Returns True if the workflow was triggered successfully

    For now, this stub acknowledges the callback with no-op success.
    The full implementation is wired through the Celery task chain
    in app.tasks.email_processing.
    """
    logger = logging.getLogger(__name__)
    logger.info("Email reply processing called for message_id=%s (stub)", message_id)
    return True
