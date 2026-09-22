"""Security-hardening regression suite (MVP bearer-token auth).

Verifies the protections added on the ``feature/security-hardening`` branch:

1. Every /api/v1 data route rejects anonymous access with 401 (health stays
   public).
2. Login verifies credentials against a PBKDF2-HMAC-SHA256 hash and issues a
   signed, expiring bearer token; invalid/expired/tampered tokens are 401.
3. Logout server-revokes the token so it can no longer authenticate.
4. Login attempts are throttled per client IP (429 on abuse).
5. Validation reviewer identity is derived from the authenticated session, so
   the HSE audit trail cannot be forged.
6. 500 error bodies never leak internal exception detail.
7. Security headers are present on API responses.
8. Authentication events land in the internal audit trail.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

import pytest
from fastapi.testclient import TestClient

# Configure the demo identity + a fixed signing secret BEFORE importing the
# application so pydantic-settings picks them up. AUTH_MAX_ATTEMPTS is lowered
# to keep the throttle test fast.
os.environ["AUTH_ENABLED"] = "true"
os.environ["AUTH_EMAIL"] = "hse.analyst@oilindia.in"
os.environ["AUTH_PASSWORD"] = "mechora2026"
os.environ["AUTH_SECRET"] = "mechora-test-secret"
os.environ["AUTH_MAX_ATTEMPTS"] = "3"

from app.config import get_settings  # noqa: E402
from app.database import repos  # noqa: E402
from app.main import create_app  # noqa: E402
from app.security.auth import reset_throttle_state  # noqa: E402


EMAIL = "hse.analyst@oilindia.in"
PASSWORD = "mechora2026"

PROTECTED_ENDPOINTS = [
    "/api/v1/observations",
    "/api/v1/families",
    "/api/v1/dashboard",
    "/api/v1/capas",
    "/api/v1/ontology",
    "/api/v1/evaluation/latest",
    "/api/v1/aggregates/barrier",
]


@pytest.fixture(autouse=True)
def _reset_throttle():
    reset_throttle_state()
    yield


@pytest.fixture()
def client():
    with TestClient(create_app()) as c:
        yield c
    # Release the SQLite connection so conftest can reset the test DB file
    # (Windows holds the WAL file open otherwise).
    from app.database import engine as _db_engine

    _db_engine.dispose()


def _login(client, email=EMAIL, password=PASSWORD) -> str:
    res = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert body["user"]["email"] == email
    return body["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _expired_token() -> str:
    secret = os.environ["AUTH_SECRET"].encode("utf-8")
    now = int(time.time())
    payload = {
        "sub": EMAIL,
        "name": "HSE Safety Analyst",
        "iat": now - 7200,
        "exp": now - 3600,
    }
    body_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(body_json).rstrip(b"=").decode("ascii")
    sig = hmac.new(secret, body.encode("ascii"), hashlib.sha256).digest()
    return body + "." + base64.urlsafe_b64encode(sig).rstrip(b"=").decode("ascii")


def _tampered(token: str) -> str:
    flip = "A" if token[-1] != "A" else "B"
    return token[:-1] + flip


# --------------------------------------------------------------------------
# Access control
# --------------------------------------------------------------------------


def test_health_and_metadata_stay_public(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_protected_endpoints_reject_anonymous(client):
    for path in PROTECTED_ENDPOINTS:
        res = client.get(path)
        assert res.status_code == 401, (path, res.status_code)
        body = res.json()
        assert body["detail"] in (
            "authentication required",
            "invalid or expired token",
        )


def test_valid_token_gains_access(client):
    token = _login(client)
    for path in PROTECTED_ENDPOINTS:
        res = client.get(path, headers=_auth(token))
        # 200 for populated endpoints, 404 is an honest empty-state (evaluations)
        assert res.status_code in (200, 404), (path, res.status_code)


def test_invalid_expired_and_tampered_tokens_rejected(client):
    token = _login(client)
    bad_tokens = [
        "not-a-real-token",
        _tampered(token),
        _expired_token(),
        "Bearer " + token,  # double scheme misuse handled by parser
    ]
    for bad in bad_tokens:
        res = client.get(
            "/api/v1/observations", headers={"Authorization": f"Bearer {bad}"}
        )
        assert res.status_code == 401, bad

    for scheme in ("", "Token", "Basic"):
        res = client.get(
            "/api/v1/observations",
            headers={"Authorization": f"{scheme} {token}" if scheme else token},
        )
        assert res.status_code == 401, scheme


# --------------------------------------------------------------------------
# Credential verification & token lifecycle
# --------------------------------------------------------------------------


def test_login_rejects_bad_credentials(client):
    for email, password in (
        (EMAIL, "wrong-password"),
        ("spoof@oilindia.in", PASSWORD),
        ("", ""),
    ):
        res = client.post(
            "/api/v1/auth/login", json={"email": email, "password": password}
        )
        # wrong credentials -> 401; schema-invalid empty fields -> 422; never 200
        assert res.status_code in (401, 422), (email, res.status_code)
        if res.status_code == 401:
            assert "invalid email or password" in res.json()["detail"]
        assert "access_token" not in res.text


def test_logout_revokes_token(client):
    token = _login(client)
    assert client.get("/api/v1/observations", headers=_auth(token)).status_code == 200
    res = client.post("/api/v1/auth/logout", headers=_auth(token))
    assert res.status_code == 204
    assert client.get("/api/v1/observations", headers=_auth(token)).status_code == 401


def test_login_attempts_are_throttled(client):
    for _ in range(3):
        res = client.post(
            "/api/v1/auth/login", json={"email": EMAIL, "password": "wrong"}
        )
        assert res.status_code == 401
    res = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert res.status_code == 429
    assert "retry-after" in {k.lower() for k in res.headers.keys()}


def test_password_hash_roundtrip():
    from app.security.auth import hash_password, verify_password

    digest = hash_password("S3cret!demo")
    assert digest.startswith("pbkdf2_sha256$")
    assert verify_password("S3cret!demo", digest)
    assert not verify_password("wrong", digest)
    assert not verify_password("S3cret!demo", "plaintext-not-a-hash")


def test_password_never_returned_by_login(client):
    res = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD}
    )
    assert res.status_code == 200
    assert PASSWORD not in res.text
    assert "access_token" in res.json()


# --------------------------------------------------------------------------
# Identity-aware audit trail & 500 hygiene
# --------------------------------------------------------------------------


def test_validation_reviewer_derived_from_session(client):
    from app.services.normalization.ontology import get_ontology
    from app.services.pipeline import AnalysisPipeline

    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    obs = pipeline.to_observation(
        "SEC-REV-1",
        "Flange joint opened without verifying zero energy; gas released.",
        provider="rules",
    )
    saved = repos.create_observation(obs, recompute=False)

    token = _login(client)
    res = client.patch(
        f"/api/v1/observations/{saved.id}/validation",
        headers=_auth(token),
        json={"status": "validated"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["validation"] == "validated"
    assert body["validation_reviewer"] == EMAIL
    assert body["validation_reason"] == ""


def test_500_error_detail_is_sanitized(client, monkeypatch):
    class BoomPipeline:
        def analyze(self, report_id, narrative, provider=None):  # noqa: ARG002
            raise RuntimeError("boom-internal-sql-detail")

    monkeypatch.setattr("app.api.routes.analyze.get_pipeline", lambda _s: BoomPipeline())

    token = _login(client)
    res = client.post(
        "/api/v1/analyze",
        headers=_auth(token),
        json={
            "report_id": "SEC-500",
            "narrative": "Flange joint opened without verifying zero energy; gas released.",
            "provider": "rules",
        },
    )
    assert res.status_code == 500
    assert res.json()["detail"] == "analysis failed"
    assert "boom-internal-sql-detail" not in res.text


def test_security_headers_present(client):
    res = client.get("/api/v1/health")
    headers = {k.lower(): v for k, v in res.headers.items()}
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "strict-origin-when-cross-origin"
    assert headers["content-security-policy"] == "default-src 'none'"
    assert headers["strict-transport-security"].startswith("max-age=")


def test_audit_trail_records_auth_events(client):
    token = _login(client)
    assert token
    res = client.post(
        "/api/v1/auth/login", json={"email": EMAIL, "password": "wrong"}
    )
    assert res.status_code == 401

    entries = repos.audit_entries()
    actions = [e["action"] for e in entries]
    assert "auth.login_success" in actions
    assert "auth.login_failed" in actions


def test_provider_literal_is_enforced(client):
    token = _login(client)
    res = client.post(
        "/api/v1/analyze",
        headers=_auth(token),
        json={
            "report_id": "SEC-P-1",
            "narrative": "Flange joint opened without verifying zero energy; gas released.",
            "provider": "bogus-provider",
        },
    )
    assert res.status_code == 422


def test_audit_trail_records_validation_change(client):
    from app.services.normalization.ontology import get_ontology
    from app.services.pipeline import AnalysisPipeline

    pipeline = AnalysisPipeline(get_ontology(), get_settings())
    obs = pipeline.to_observation(
        "SEC-REV-2",
        "Pump casing opened without zero energy verification; gas escaped.",
        provider="rules",
    )
    saved = repos.create_observation(obs, recompute=False)

    token = _login(client)
    res = client.patch(
        f"/api/v1/observations/{saved.id}/validation",
        headers=_auth(token),
        json={"status": "rejected", "reason": "does not match field report"},
    )
    assert res.status_code == 200

    actions = [e["action"] for e in repos.audit_entries()]
    assert "observation.validation" in actions
    entry = next(e for e in repos.audit_entries() if e["action"] == "observation.validation")
    assert entry["actor"] == EMAIL
    assert "rejected" in entry["detail"]