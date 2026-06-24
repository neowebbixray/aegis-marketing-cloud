#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Aegis Marketing Cloud — Backend Dev Entrypoint
# Waits for DB (extracts creds from DATABASE_URL), runs
# alembic migrations, then starts the app.
# ─────────────────────────────────────────────────────────────
set -euo pipefail

echo "→ Waiting for database..."
python -c "
import os, re, asyncio, asyncpg

url = os.environ['DATABASE_URL']
m = re.match(r'postgresql\+asyncpg://([^:]+):([^@]+)@([^:]+):(\d+)/(.+)', url)
if not m:
    raise SystemExit(f'Cannot parse DATABASE_URL: {url}')
user, pw, host, port, db = m.groups()

async def wait():
    for i in range(30):
        try:
            conn = await asyncpg.connect(user=user, password=pw, database=db, host=host, port=int(port))
            await conn.close()
            return
        except Exception:
            if i < 29:
                import time; time.sleep(1)
    raise SystemExit(1)

asyncio.run(wait())
"
echo "✓ Database is ready"

echo "→ Running alembic migrations..."
alembic upgrade head
echo "✓ Migrations applied"

echo "→ Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug
