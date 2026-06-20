# Quick Start

The following steps get a local development environment up and running.  All commands assume you have **Docker** and **Docker Compose** installed.

```bash
# 1. Clone the repository
git clone https://github.com/nousresearch/aegis-marketing-cloud.git
cd aegis-marketing-cloud

# 2. Copy the example environment file (do NOT commit real secrets)
cp src/backend/.env.example src/backend/.env

# 3. (Optional) Run the Windows‑specific test runner (useful on CI)
./scripts/run_tests_windows.sh

# 4. Start the full stack (backend, frontend, databases, etc.)
#    The top‑level docker‑compose brings up all services, including Vault.
#    If you only need a subset, edit the compose file accordingly.

docker compose up -d

# 5. Apply database migrations (run inside the backend container)

docker compose exec backend alembic upgrade head

# 6. Open the UI in your browser
#    Frontend runs on port 3000, backend API on 8000.
#    Adjust `NEXT_PUBLIC_API_URL` in the frontend env if you change ports.
open http://localhost:3000
```

## After the stack is up
- The **Vault** service is available at `http://localhost:8200` with the dev token `root`.  Secrets from `src/backend/.env.example` have already been migrated into Vault by the migration script.
- The **FastAPI** docs are exposed at `http://localhost:8000/docs` (disabled in production).
- Grafana, Prometheus, Loki, and other observability components are reachable on their documented ports.

---

> For production deployments, see the `docs/DEPLOY.md` guide for Helm charts, TLS, scaling, and security hardening.
