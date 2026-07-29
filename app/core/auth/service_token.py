from __future__ import annotations

import hashlib
import secrets

from fastapi import Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config.settings import get_settings
from app.core.exceptions import DashboardAuthError

_service_bearer = HTTPBearer(
    scheme_name="ServiceAdminBearer",
    description="Service admin token",
    auto_error=False,
)


def _service_token_matches(presented: str, configured: str) -> bool:
    """Compare fixed-size digests so token length cannot affect the comparison."""

    presented_digest = hashlib.sha256(presented.encode("utf-8")).digest()
    configured_digest = hashlib.sha256(configured.encode("utf-8")).digest()
    return secrets.compare_digest(presented_digest, configured_digest)


async def validate_service_admin_token(
    credentials: HTTPAuthorizationCredentials | None = Security(_service_bearer),
) -> None:
    """Authorize the service API without sharing dashboard or proxy auth state."""

    configured = get_settings().service_admin_token
    if not configured:
        raise DashboardAuthError("Service API authentication is unavailable", code="service_auth_unavailable")

    presented = credentials.credentials if credentials is not None else None
    if not presented or not _service_token_matches(presented, configured):
        raise DashboardAuthError("Invalid service authentication", code="service_auth_invalid")
