#!/usr/bin/env python3
"""Migrate .env.example values into HashiCorp Vault (dev mode).

The script:
1. Reads ``src/backend/.env.example`` (the repository ships a safe example file).
2. Parses ``KEY=VALUE`` pairs, ignoring comments and blank lines.
3. Connects to Vault at ``http://vault:8200`` using the root token ``root``.
4. Writes all key/value pairs under the KV path ``amc`` (i.e. ``secret/data/amc``).

Running the script after starting ``docker compose up`` will populate Vault so the
backend can fetch its configuration via ``app.vault.load_vault_secrets()``.
"""
import os
import re
import sys
from pathlib import Path

try:
    import hvac
except Exception as e:
    print("hvac library not installed – aborting migration script.")
    sys.exit(1)

# Path to the example env file (always present, never contains real secrets).
ENV_EXAMPLE = Path(__file__).parent.parent / "src" / "backend" / ".env.example"
if not ENV_EXAMPLE.is_file():
    print(f"Env example file not found at {ENV_EXAMPLE}")
    sys.exit(1)

# Parse the file into a dict.
secrets = {}
with ENV_EXAMPLE.open() as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Simple KEY=VALUE split – values may contain spaces after the first =
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip().strip('"')  # strip optional surrounding quotes
        secrets[key] = val

if not secrets:
    print("No secrets found in .env.example – nothing to migrate.")
    sys.exit(0)

vault_addr = os.getenv("VAULT_ADDR", "http://vault:8200")
vault_token = os.getenv("VAULT_TOKEN", "root")
client = hvac.Client(url=vault_addr, token=vault_token)

# Ensure the KV v2 mount exists (the dev container mounts default ``secret``).
mounts = client.sys.list_mounted_secrets_engines()
if "secret/" not in mounts:
    print("Vault KV mount 'secret/' not found – aborting.")
    sys.exit(1)

# Write all secrets under the ``amc`` path.
client.secrets.kv.v2.create_or_update_secret(path="amc", secret=secrets)
print(f"Successfully migrated {len(secrets)} entries to Vault at {vault_addr}/secret/data/amc")
