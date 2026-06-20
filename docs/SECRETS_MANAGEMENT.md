# Secrets Management Guide

> **Last updated:** June 2026  
> **Applies to:** Aegis Marketing Cloud — all services, deployments, and environments

---

## Table of Contents

1. [Overview](#1-overview)
2. [Development Workflow (`.env` files)](#2-development-workflow-env-files)
3. [Production: HashiCorp Vault](#3-production-hashicorp-vault)
4. [Production: AWS Secrets Manager](#4-production-aws-secrets-manager)
5. [Production: Azure Key Vault](#5-production-azure-key-vault)
6. [Environment Variable Reference](#6-environment-variable-reference)
7. [Best Practices](#7-best-practices)
8. [Rotation & Incident Response](#8-rotation--incident-response)

---

## 1. Overview

Aegis Marketing Cloud uses **pydantic-settings** (`app/config.py`) to load
configuration from environment variables, which in turn can be sourced from
`.env` files, HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, or any
combination thereof.

**Key principle:** Secrets never appear in source code, CI logs, or image
layers.  Every environment resolves its own secrets at boot time.

### Architecture decision

| Environment     | Secret source                          | Why                                                                 |
|-----------------|----------------------------------------|---------------------------------------------------------------------|
| Development     | `.env` file (gitignored)               | Fast iteration, no infra dependency                                 |
| CI / Testing    | Repository secrets / CI vars           | Short-lived, scoped to a single workflow run                        |
| Staging         | HashiCorp Vault (or cloud secret mgr)  | Audited, versioned, centralised                                      |
| Production      | HashiCorp Vault + K8s `external-secrets` | Automatic rotation, audit trail, DR-compatible                    |

---

## 2. Development Workflow (`.env` files)

### 2.1 Setup

1. Copy the template (if one exists) or create your own:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your local values.  The file is **gitignored** by default.

3. The application loads `.env` automatically via `pydantic-settings`.  You can
   point to a different path with the `AMC_ENV_FILE` env var:

   ```bash
   export AMC_ENV_FILE=/path/to/custom.env
   ```

### 2.2 Example `.env`

```ini
# ── Application ───────────────────────────────────────────────────
ENVIRONMENT=development
DEBUG=true

# ── Database ──────────────────────────────────────────────────────
DATABASE_URL=postgresql+asyncpg://amc:amc_secret@localhost:5432/aegis_marketing_cloud

# ── Redis ─────────────────────────────────────────────────────────
REDIS_URL=redis://:aegis_redis@localhost:6379/0

# ── RabbitMQ ──────────────────────────────────────────────────────
RABBITMQ_URL=amqp://aegis:***@localhost:5672/

# ── Auth / JWT ────────────────────────────────────────────────────
SECRET_KEY=changeme
JWT_KEY_ID=default

# ── CSP overrides (optional) ──────────────────────────────────────
CSP_SCRIPT_SRC='self' 'unsafe-inline' https://example.com
CSP_REPORT_ONLY=false
```

### 2.3 What NOT to commit

- Real database passwords
- API keys (Stripe, OpenAI, AWS, etc.)
- JWT signing keys
- Encryption keys
- SMTP credentials

A `.env.example` file **with placeholder values** should be committed so new
developers know which variables to configure.

---

## 3. Production: HashiCorp Vault

### 3.1 Setup overview

Vault acts as the canonical secret store for all non-development environments.
The application reads secrets at startup via one of two strategies:

1. **Sidecar injector** (Kubernetes) — Vault Agent injects secrets as
   environment variables before the application container starts.
2. **Direct API** — the app calls Vault's KV v2 API on boot (requires a
   Vault token or Kubernetes auth).

### 3.2 Vault policy (minimum)

```hcl
path "secret/data/amc/*" {
  capabilities = ["read", "list"]
}
```

### 3.3 Secret layout

```
secret/amc/production/
├── database
│   └── DATABASE_URL
├── redis
│   └── REDIS_URL
├── auth
│   ├── SECRET_KEY
│   └── JWT_KEY_ID
├── stripe
│   ├── STRIPE_API_KEY
│   └── STRIPE_WEBHOOK_SECRET
├── aws
│   ├── AWS_ACCESS_KEY_ID
│   ├── AWS_SECRET_ACCESS_KEY
│   └── AWS_REGION
├── smtp
│   ├── SMTP_USER
│   └── SMTP_PASSWORD
├── ai
│   ├── NVIDIA_NIM_API_KEY
│   ├── OPENAI_API_KEY
│   └── ANTHROPIC_API_KEY
└── encryption
    └── ENCRYPTION_KEY
```

### 3.4 Startup integration (Kubernetes + external-secrets)

```yaml
# Example ExternalSecret manifest
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: amc-secrets
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: ClusterSecretStore
    name: vault-backend
  target:
    name: amc-env-vars
  data:
    - secretKey: DATABASE_URL
      remoteRef:
        key: secret/data/amc/production/database
        property: DATABASE_URL
    - secretKey: STRIPE_API_KEY
      remoteRef:
        key: secret/data/amc/production/stripe
        property: STRIPE_API_KEY
    # … repeat for every secret
```

---

## 4. Production: AWS Secrets Manager

### 4.1 Setup

If you're already on AWS, Secrets Manager provides automatic rotation and
fine-grained IAM policies.

### 4.2 IAM policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:us-east-1:123456789012:secret:amc/*"
    }
  ]
}
```

### 4.3 Secret layout

Store each environment variable as a separate secret (or a single JSON blob):

```bash
aws secretsmanager create-secret \
  --name amc/production/database-url \
  --secret-string "postgresql+asyncpg://..." \
  --region us-east-1

aws secretsmanager create-secret \
  --name amc/production/stripe-api-key \
  --secret-string "sk_live_..." \
  --region us-east-1
```

### 4.4 Startup integration

```python
# Stub — extends pydantic-settings with AWS Secrets Manager
# import boto3
# client = boto3.client("secretsmanager")
# value = client.get_secret_value(SecretId="amc/production/database-url")
# os.environ["DATABASE_URL"] = value["SecretString"]
```

For Kubernetes, use the **AWS Secrets & Configuration Provider (ASCP)** or
**external-secrets** operator.

---

## 5. Production: Azure Key Vault

### 5.1 Setup

Azure Key Vault integrates natively with Azure-managed workloads via Managed
Identities.

### 5.2 Secret layout

```
https://amc-kv.vault.azure.net/
├── secrets/database-url
├── secrets/stripe-api-key
├── secrets/aws-access-key-id
├── secrets/aws-secret-access-key
├── secrets/smtp-password
└── secrets/encryption-key
```

### 5.3 Startup integration

```python
# Stub — extends pydantic-settings with Azure Key Vault
# from azure.identity import DefaultAzureCredential
# from azure.keyvault.secrets import SecretClient
# client = SecretClient(vault_url="https://amc-kv.vault.azure.net",
#                       credential=DefaultAzureCredential())
# secret = client.get_secret("database-url")
# os.environ["DATABASE_URL"] = secret.value
```

For Kubernetes, use the **Azure Key Vault Provider for Secrets Store CSI
Driver** or **external-secrets**.

---

## 6. Environment Variable Reference

All variables are defined in `app/config.py` with types, defaults, and aliases.
Below is a quick reference of **sensitive** variables that must be protected.

| Variable                     | Sensitivity | Description                                    |
|------------------------------|-------------|------------------------------------------------|
| `SECRET_KEY`                 | 🔴 Critical | JWT signing private key (PEM)                  |
| `ENCRYPTION_KEY`             | 🔴 Critical | AES-256 key for column-level encryption        |
| `DATABASE_URL`               | 🔴 Critical | Full connection string (includes password)     |
| `REDIS_URL`                  | 🟠 High     | Redis connection string (includes password)    |
| `STRIPE_API_KEY`             | 🟠 High     | Stripe secret key (live mode)                  |
| `STRIPE_WEBHOOK_SECRET`      | 🟠 High     | Stripe webhook signing secret                  |
| `AWS_ACCESS_KEY_ID`          | 🟠 High     | AWS IAM access key                             |
| `AWS_SECRET_ACCESS_KEY`      | 🟠 High     | AWS IAM secret key                             |
| `SMTP_USER` / `SMTP_PASSWORD`| 🟠 High     | SMTP credentials                               |
| `NVIDIA_NIM_API_KEY`         | 🟠 High     | NVIDIA NIM API key                             |
| `OPENAI_API_KEY`             | 🟠 High     | OpenAI API key                                 |
| `ANTHROPIC_API_KEY`          | 🟠 High     | Anthropic API key                              |
| `MINIO_ACCESS_KEY` / `MINIO_SECRET_KEY` | 🟠 High | MinIO / S3 credentials                  |
| `SENTRY_DSN`                 | 🟡 Medium   | Sentry DSN (contains project key)             |
| `JWT_KEY_ID`                 | 🟡 Medium   | Key identifier for JWK rotation               |

---

## 7. Best Practices

### 7.1 General

1. **Never hard-code secrets** — use env vars or a secret store.
2. **Never log secrets** — configure log filters to redact known secret
   patterns (e.g. ``sk_live_*``, ``-----BEGIN.*PRIVATE KEY-----``).
3. **Use short-lived credentials** — Vault dynamic secrets, STS tokens, or
   auto-rotated keys.
4. **Audit every access** — every secret read should be logged and monitored.
5. **Separate secrets by environment** — never reuse production secrets in
   staging or development.
6. **Encrypt at rest and in transit** — TLS for transport, KMS/Vault for
   storage.

### 7.2 `.env` file security

- Add `.env` to ``.gitignore`` immediately.
- Never share `.env` files via chat, email, or support tickets.
- Rotate development secrets periodically (especially if shared across a team).
- Consider using **`direnv`** or **`dotenv-linter`** to validate the file.

### 7.3 CI/CD security

- Use **GitHub Actions secrets** or **GitLab CI variables** — never plain-text
  env vars in workflow files.
- Mask secrets in logs by default (GitHub Actions does this automatically for
  secrets).
- Limit which branches / actions can access production secrets.
- Use OIDC (OpenID Connect) for cloud provider access instead of long-lived
  keys.

### 7.4 Incident response

| Scenario                        | Action                                                                 |
|---------------------------------|------------------------------------------------------------------------|
| Secret leaked in log / output   | Rotate the secret immediately. Delete the log entry if possible.       |
| `.env` file committed           | Rotate all secrets in that file. Use `git-filter-repo` to purge git.   |
| Stolen Vault token              | Revoke the token. Rotate all secrets the token could access.           |
| Compromised CI secret           | Rotate the secret. Audit recent workflow runs for exfiltration.        |

---

## 8. Rotation & Incident Response

### 8.1 Manual rotation (any environment)

1. Generate a new value.
2. Update the secret in Vault / AWS / Azure.
3. Restart the affected service(s).
4. Verify the old credential no longer works.
5. Log the rotation in the security audit trail.

### 8.2 Automated rotation (Vault)

Vault's **database secrets engine** and **PKI secrets engine** support
lease-based automatic rotation.  For static secrets, use a cron-driven
rotation workflow:

```bash
# Example: rotate Stripe key
vault write secret/amc/production/stripe STRIPE_API_KEY="$(openssl rand -base64 32)"
kubectl rollout restart deployment/amc-api
```

### 8.3 Key rotation schedule

| Secret type        | Recommended rotation | Notes                                    |
|--------------------|---------------------|------------------------------------------|
| JWT signing keys   | Every 90 days       | Keep previous key in JWKS during overlap |
| Database passwords | Every 180 days      | Use zero-downtime rotation              |
| API keys (Stripe…) | Every 365 days      | Coordinate with provider                 |
| Encryption keys    | Every 365 days      | Re-encrypt data with new key             |
| Service tokens     | Every 30 days       | Use short-lived tokens where possible    |

---

**Questions?** Contact the Security Engineering team or open a ticket in
`#security` on Slack.
