"""Security utilities: JWT creation/verification (RS256), password hashing,
API key generation, and ULID-style ID creation.

The documentation mandates:
- RS256 (asymmetric) with 4096-bit RSA keys
- Access tokens: 15 minute TTL
- Refresh tokens: 7 day sliding TTL (max 30 days absolute)
"""

from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import bcrypt
from jose import jwt

from app.config import settings
from app.core.keys import get_private_key, get_public_key

# ── Password hashing (bcrypt, cost factor 12) ────────────────────────────────
_BCRYPT_ROUNDS = 12


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain* (cost factor 12)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)).decode(
        "utf-8"
    )


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` if *plain* matches the bcrypt *hashed* value."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── JWT (RS256) ──────────────────────────────────────────────────────────────
ALGORITHM = "RS256"
ISS = "amc.io/auth"
AUD = "amc.io/api"


def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create an RS256-signed JWT access token.

    Args:
        subject: The user ID (``usr_`` prefixed) as the ``sub`` claim.
        extra_claims: Optional claims such as ``tenant_id``, ``workspace_id``,
                      ``roles``, ``scopes``.
        expires_delta: Token lifetime (defaults to 15 minutes).

    Returns:
        Encoded JWT string with headers ``{"alg": "RS256", "typ": "JWT", "kid": "<kid>"}``.

    """
    now = datetime.now(UTC)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire)

    kid = settings.jwt_key_id
    payload: dict[str, Any] = {
        "sub": subject,
        "iss": ISS,
        "aud": AUD,
        "iat": now,
        "exp": now + expires_delta,
        "type": "access",
        "jti": uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)

    private_key = get_private_key(kid)
    return jwt.encode(
        payload,
        private_key,
        algorithm=ALGORITHM,
        headers={"kid": kid, "typ": "JWT"},
    )


def create_refresh_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create an RS256-signed JWT refresh token (longer-lived, 7 days)."""
    now = datetime.now(UTC)
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_refresh_token_expire)

    kid = settings.jwt_key_id
    payload: dict[str, Any] = {
        "sub": subject,
        "iss": ISS,
        "aud": AUD,
        "iat": now,
        "exp": now + expires_delta,
        "type": "refresh",
        "jti": uuid4().hex,
    }
    if extra_claims:
        payload.update(extra_claims)

    private_key = get_private_key(kid)
    return jwt.encode(
        payload,
        private_key,
        algorithm=ALGORITHM,
        headers={"kid": kid, "typ": "JWT"},
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate an RS256 JWT token.

    Uses the public key associated with the token's ``kid`` header.

    Raises:
        jose.JWTError: If the token is expired, malformed, or signature invalid.

    """
    # Extract kid from the unverified header so we know which key to use
    from jose import jws

    header_data = jws.get_unverified_header(token)
    kid = header_data.get("kid", settings.jwt_key_id)
    public_key = get_public_key(kid)

    return jwt.decode(
        token,
        public_key,
        algorithms=[ALGORITHM],
        audience=AUD,
        issuer=ISS,
        options={"verify_aud": True, "verify_iss": True},
    )


# ── API Key ──────────────────────────────────────────────────────────────────
def generate_api_key() -> tuple[str, str]:
    """Generate a cryptographically random API key.

    Returns a tuple of ``(full_key, key_prefix)`` where *full_key* is the
    value to return to the caller (shown once) and *key_prefix* is the first
    8 characters stored for identification.

    Format: ``amc_<24-hex-chars>``  (prefixed, 8-char prefix).
    """
    random_bytes = secrets.token_hex(24)  # 48 hex chars
    prefix = "amc_" + random_bytes[:8]
    full_key = prefix + random_bytes[8:]
    return full_key, prefix


def hash_api_key(raw_key: str) -> str:
    """Return a SHA-256 hex digest of *raw_key* for storage."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


# ── ULID-style ID generation ────────────────────────────────────────────────
def create_ulid(prefix: str) -> str:
    """Create a ULID-style identifier with a human-readable *prefix*.

    Example::

        >>> create_ulid("cont")
        'cont_01HRA5YTP9Z2X8K4W6Q3FV7J1A'

    Uses ``uuid6.uuid7()`` for time-sortable IDs, encoded as Crockford-style
    base32 URL-safe.
    """
    try:
        import uuid6

        uid = uuid6.uuid7()
    except ImportError:
        uid = uuid4()

    raw = uid.bytes
    encoded = base64.b32hexencode(raw).decode("ascii").rstrip("=")
    return f"{prefix}_{encoded}"
