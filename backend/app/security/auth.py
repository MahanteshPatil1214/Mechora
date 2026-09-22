"""Secure demo authentication for the MECHORA API.

MVP bearer-token auth with zero additional dependencies:

- Passwords are verified against a PBKDF2-HMAC-SHA256 hash. A plaintext demo
  password from config is hashed in memory at verification time; it is never
  stored, logged, or returned by the API.
- Sessions are stateless, HMAC-SHA256 signed tokens carrying ``sub`` / ``iat`` /
  ``exp``. Signatures are compared with constant-time ``hmac.compare_digest``.
- Logout is enforced with a server-side in-memory revocation set (restart
  clears sessions; acceptable for the SIH prototype).
- Login attempts are throttled per client IP to slow brute force.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

logger = logging.getLogger("mechora.security")

_PBKDF2_ROUNDS = 600_000
_HASH_SCHEME = "pbkdf2_sha256"


@dataclass(frozen=True)
class AuthIdentity:
    """The authenticated HSE principal bound to a signed session token."""

    email: str
    name: str
    role: str
    organization: str

    @property
    def display_name(self) -> str:
        return self.name or self.email


# --------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# --------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256 + random salt (constant-time
    comparison friendly, no external dependency)."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), _PBKDF2_ROUNDS
    )
    return f"{_HASH_SCHEME}${_PBKDF2_ROUNDS}${salt}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time verification of a password against a stored hash."""
    try:
        scheme, rounds, salt, digest_hex = stored.split("$", 3)
        if scheme != _HASH_SCHEME:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(rounds)
        )
        return hmac.compare_digest(dk.hex(), digest_hex)
    except Exception:  # noqa: BLE001 - malformed config must fail closed
        return False


def verify_credentials(email: str, password: str) -> AuthIdentity | None:
    """Check email/password against the configured demo identity.

    Returns None on any mismatch so callers always issue the same generic 401.
    """
    settings = get_settings()
    email = (email or "").strip().lower()
    if not email or not password:
        return None
    if not hmac.compare_digest(email, settings.auth_email.lower()):
        return None
    stored = settings.auth_password_hash or (
        hash_password(settings.auth_password) if settings.auth_password else ""
    )
    if not stored:
        return None  # fail closed: no credential configured
    if not verify_password(password, stored):
        return None
    return AuthIdentity(
        email=settings.auth_email,
        name=settings.auth_identity_name,
        role=settings.auth_identity_role,
        organization=settings.auth_identity_organization,
    )


# --------------------------------------------------------------------------
# Signed session tokens (HMAC-SHA256)
# --------------------------------------------------------------------------

_AUTO_SECRET = secrets.token_bytes(32)


def _signing_secret() -> bytes:
    configured = get_settings().auth_secret
    if configured:
        return configured.encode("utf-8")
    return _AUTO_SECRET


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


def create_token(identity: AuthIdentity, ttl_seconds: int | None = None) -> str:
    """Issue a stateless signed token for ``identity``."""
    settings = get_settings()
    if ttl_seconds is None:
        ttl_seconds = int(settings.auth_token_ttl_hours * 3600)
    now = int(time.time())
    payload = {
        "sub": identity.email,
        "name": identity.name,
        "iat": now,
        "exp": now + max(60, ttl_seconds),
    }
    body = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(_signing_secret(), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(signature)}"


def decode_token(token: str) -> AuthIdentity | None:
    """Verify signature + expiry and return the bound identity (or None)."""
    try:
        body, signature = token.rsplit(".", 1)
        expected = hmac.new(
            _signing_secret(), body.encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(_b64url_decode(signature), expected):
            return None
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
        if int(payload.get("exp", 0)) < int(time.time()):
            return None
        email = str(payload.get("sub", ""))
        if not email:
            return None
        return AuthIdentity(
            email=email,
            name=str(payload.get("name", "")),
            role=get_settings().auth_identity_role,
            organization=get_settings().auth_identity_organization,
        )
    except Exception:  # noqa: BLE001 - malformed/foreign token
        return None


# --------------------------------------------------------------------------
# Logout revocation (in-memory)
# --------------------------------------------------------------------------

# token sha256 hexdigest -> expires-at (epoch)
_revoked: dict[str, int] = {}


def _token_id(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def revoke_token(token: str) -> None:
    """Revoke a still-valid token. Re-verification of the same token must fail
    from now on (until the process restarts)."""
    identity = decode_token(token)
    if identity is None:
        return
    parsed = _parse_exp(token)
    if parsed is not None:
        _revoked[_token_id(token)] = parsed
    _prune_revoked()


def _parse_exp(token: str) -> int | None:
    try:
        body, _ = token.rsplit(".", 1)
        payload = json.loads(_b64url_decode(body).decode("utf-8"))
        return int(payload.get("exp", 0))
    except Exception:  # noqa: BLE001
        return None


def _prune_revoked() -> None:
    now = int(time.time())
    expired = [t for t, exp in _revoked.items() if exp < now]
    for t in expired:
        _revoked.pop(t, None)


def is_revoked(token: str) -> bool:
    _prune_revoked()
    return _token_id(token) in _revoked


# --------------------------------------------------------------------------
# FastAPI dependency
# --------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)

_WWW_BEARER = {"WWW-Authenticate": "Bearer"}


def require_auth(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> AuthIdentity:
    """FastAPI dependency enforcing bearer-token auth on a route/router.

    Public when ``auth_enabled`` is false (explicit config opt-out); otherwise
    a missing/invalid/expired/revoked token is rejected with HTTP 401.
    """
    settings = get_settings()
    if not settings.auth_enabled:
        return AuthIdentity("local", "Local", "rules", "local")
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="authentication required", headers=_WWW_BEARER)
    token = credentials.credentials
    identity = decode_token(token)
    if identity is None or is_revoked(token):
        raise HTTPException(status_code=401, detail="invalid or expired token", headers=_WWW_BEARER)
    return identity


def bearer_credentials(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> HTTPAuthorizationCredentials | None:
    """Optional dependency returning the raw parsed Authorization header."""
    return credentials


# --------------------------------------------------------------------------
# Login throttling (in-memory, per client IP)
# --------------------------------------------------------------------------

# ip -> sorted list of recent attempt timestamps
_login_attempts: dict[str, list[float]] = {}


def check_login_allowed(client_ip: str) -> None:
    """Raise 429 when ``client_ip`` has exceeded the configured attempt budget."""
    settings = get_settings()
    max_attempts = max(1, settings.auth_max_attempts)
    window = max(1, settings.auth_lockout_seconds)
    now = time.time()
    recent = [t for t in _login_attempts.get(client_ip, []) if now - t < window]
    _login_attempts[client_ip] = recent
    if len(recent) >= max_attempts:
        retry = int(window - (now - recent[0])) + 1
        raise HTTPException(
            status_code=429,
            detail="too many login attempts; try again later",
            headers={"Retry-After": str(retry)},
        )


def record_login_attempt(client_ip: str) -> None:
    timestamp = time.time()
    _login_attempts.setdefault(client_ip, []).append(timestamp)


def clear_login_attempts(client_ip: str) -> None:
    _login_attempts.pop(client_ip, None)


def reset_throttle_state() -> None:
    """Test hook: clear all in-memory throttle state."""
    _login_attempts.clear()