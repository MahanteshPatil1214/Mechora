"""Authentication endpoints (MVP proof-of-concept bearer-token auth).

Login verifies the configured HSE demo identity against a PBKDF2-HMAC-SHA256
hash and returns a short-lived signed bearer token. Logout revokes the token
server-side. All other /api/v1 data routes require the token.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from app.config import get_settings
from app.database import repos
from app.security.auth import (
    AuthIdentity,
    bearer_credentials,
    check_login_allowed,
    clear_login_attempts,
    create_token,
    record_login_attempt,
    require_auth,
    revoke_token,
    verify_credentials,
)

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: dict


@router.post("/auth/login", response_model=LoginResponse)
def login(request: Request, body: LoginRequest) -> LoginResponse:
    settings = get_settings()
    if not settings.auth_enabled:
        raise HTTPException(
            status_code=403,
            detail="authentication is disabled on this instance",
        )
    client_ip = request.client.host if request.client else "unknown"
    check_login_allowed(client_ip)
    record_login_attempt(client_ip)

    identity = verify_credentials(body.email, body.password)
    if identity is None:
        repos.audit_log(
            "auth.login_failed", actor=(body.email or "").strip(), detail=client_ip
        )
        raise HTTPException(
            status_code=401,
            detail="invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    clear_login_attempts(client_ip)
    ttl_seconds = int(settings.auth_token_ttl_hours * 3600)
    token = create_token(identity, ttl_seconds=ttl_seconds)
    repos.audit_log(
        "auth.login_success",
        actor=identity.email,
        detail=f"session issued for {ttl_seconds}s from {client_ip}",
    )
    return LoginResponse(
        access_token=token,
        token_type="bearer",
        expires_in=ttl_seconds,
        user={
            "email": identity.email,
            "name": identity.display_name,
            "role": identity.role,
            "organization": identity.organization,
        },
    )


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request,
    identity: AuthIdentity = Depends(require_auth),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_credentials),
) -> Response:
    """Revoke the presented token so it can no longer authenticate."""
    if credentials is not None and credentials.credentials:
        revoke_token(credentials.credentials)
        repos.audit_log(
            "auth.logout",
            actor=identity.email,
            detail=request.client.host if request.client else "unknown",
        )
    return Response(status_code=204)