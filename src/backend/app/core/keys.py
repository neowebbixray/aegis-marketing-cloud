"""RSA key management for RS256 JWT signing.

Generates, loads, and caches RSA key pairs used for JWT creation and
verification.  In production the private key should be stored in HashiCorp
Vault; in development / CI a file-based fallback is provided.
"""

from __future__ import annotations

import logging
from pathlib import Path

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

log = logging.getLogger(__name__)

_KEY_DIR = Path(__file__).resolve().parent / "keys"


def _ensure_key_dir() -> Path:
    _KEY_DIR.mkdir(parents=True, exist_ok=True)
    return _KEY_DIR


def _key_path(kid: str = "default") -> tuple[Path, Path]:
    """Return ``(private_key_path, public_key_path)`` for *kid*."""
    d = _ensure_key_dir()
    return d / f"{kid}.pem", d / f"{kid}.pub.pem"


# ── In-memory cache ──────────────────────────────────────────────────────────
_private_key_cache: dict[str, rsa.RSAPrivateKey] = {}
_public_key_cache: dict[str, rsa.RSAPublicKey] = {}


def get_or_create_rsa_keypair(kid: str = "default") -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Return an RSA key pair for the given *kid*, creating it if necessary."""
    if kid in _private_key_cache:
        return _private_key_cache[kid], _public_key_cache[kid]

    priv_path, pub_path = _key_path(kid)

    if priv_path.exists() and pub_path.exists():
        log.info("Loading existing RSA key pair for kid=%s from %s", kid, priv_path)
        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend(),
            )
        with open(pub_path, "rb") as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend(),
            )
    else:
        log.info("Generating new RSA 4096-bit key pair for kid=%s", kid)
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
            backend=default_backend(),
        )
        public_key = private_key.public_key()

        # Persist for reuse across restarts
        with open(priv_path, "wb") as f:
            f.write(
                private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption(),
                ),
            )
        with open(pub_path, "wb") as f:
            f.write(
                public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo,
                ),
            )

    _private_key_cache[kid] = private_key
    _public_key_cache[kid] = public_key
    return private_key, public_key


def get_private_key(kid: str = "default") -> rsa.RSAPrivateKey:
    """Get or create the RSA private key for *kid*."""
    priv, _ = get_or_create_rsa_keypair(kid)
    return priv


def get_public_key(kid: str = "default") -> rsa.RSAPublicKey:
    """Get or create the RSA public key for *kid*."""
    _, pub = get_or_create_rsa_keypair(kid)
    return pub


def get_jwks(kid: str = "default") -> dict:
    """Return a JWKS-compatible JSON dict for the current public key."""
    public_key = get_public_key(kid)
    # Build the JWKS entry manually
    pub_numbers = public_key.public_numbers()

    import base64

    def _int_to_base64url(n: int) -> str:
        """Encode an integer as a base64url-encoded big-endian byte string."""
        num_bytes = (n.bit_length() + 7) // 8
        raw = n.to_bytes(num_bytes, byteorder="big")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    jwk = {
        "kty": "RSA",
        "alg": "RS256",
        "use": "sig",
        "kid": kid,
        "n": _int_to_base64url(pub_numbers.n),
        "e": _int_to_base64url(pub_numbers.e),
    }

    return {"keys": [jwk]}
