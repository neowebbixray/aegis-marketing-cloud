"""
Vault integration helper for Aegis Marketing Cloud.

If the environment variable ``VAULT_ADDR`` is defined, this module will connect to
HashiCorp Vault (dev mode, token = ``root``) and pull any secrets stored under
``secret/data/amc``. Each key/value pair is injected into ``os.environ`` so the
standard ``pydantic-settings`` loader picks them up as if they were defined in
the ``.env`` file.

The function is deliberately lightweight and safe – if Vault is unreachable or the
path does not exist, it logs a warning and continues without altering the current
environment.
"""

from __future__ import annotations

import os
import logging
from typing import Any, Dict

logger = logging.getLogger("amc.vault")


def _fetch_secrets() -> Dict[str, Any] | None:
    """Connect to Vault and return the secret dict.

    Returns ``None`` on any error (network, auth, path not found). The caller can
    decide whether to bail out or continue.
    """
    vault_addr = os.getenv("VAULT_ADDR")
    if not vault_addr:
        return None
    try:
        import hvac
    except Exception as exc:
        logger.warning("hvac library not installed – cannot read Vault: %s", exc)
        return None
    try:
        client = hvac.Client(url=vault_addr, token=os.getenv("VAULT_TOKEN", "root"))
        # In dev mode the secret is stored under ``secret/data/<path>``
        secret_path = os.getenv("VAULT_SECRET_PATH", "secret/data/amc")
        read = client.secrets.kv.v2.read_secret_version(path=secret_path.split("secret/data/")[1])
        return read.get("data", {}).get("data", {})
    except Exception as exc:
        logger.warning("Failed to fetch secrets from Vault at %s: %s", vault_addr, exc)
        return None


def load_vault_secrets() -> None:
    """Populate ``os.environ`` with secrets from Vault (if configured)."""
    secrets = _fetch_secrets()
    if not secrets:
        logger.info("Vault not configured or no secrets found – skipping.")
        return
    for key, value in secrets.items():
        # Do not overwrite explicitly set env vars – respect developer overrides.
        if os.getenv(key) is None:
            os.environ[key] = str(value)
            logger.debug("Vault secret loaded: %s", key)
    logger.info("Loaded %d secret(s) from Vault.", len(secrets))
