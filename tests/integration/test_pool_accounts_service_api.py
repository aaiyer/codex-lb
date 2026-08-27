from __future__ import annotations

import asyncio
import base64
import json
import logging
from typing import cast

import pytest
from sqlalchemy import select, update

from app.core import routing_pause
from app.core.audit.service import drain_audit_log_tasks
from app.core.auth import generate_unique_account_id
from app.core.auth import service_token as service_token_module
from app.core.config.settings import get_settings
from app.db.models import Account, AuditLog, RequestLog
from app.db.session import SessionLocal
from app.modules.accounts import service_api as service_api_module
from app.modules.accounts.deletion import run_account_deletion_pass

pytestmark = pytest.mark.integration

SERVICE_TOKEN = "synthetic-service-admin-token-001-abcdef"
SYNTHETIC_ACCESS = "synthetic-access-credential"
SYNTHETIC_REFRESH = "synthetic-refresh-credential"
SYNTHETIC_ID = "synthetic-id-credential"


def _encode_jwt(payload: dict[str, object]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    body = base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")
    return f"header.{body}.sig"


def _make_auth_json(raw_account_id: str, email: str, plan_type: str = "plus") -> dict[str, object]:
    payload = {
        "email": email,
        "chatgpt_account_id": raw_account_id,
        "https://api.openai.com/auth": {"chatgpt_plan_type": plan_type},
    }
    return {
        "tokens": {
            "idToken": _encode_jwt(payload),
            "accessToken": SYNTHETIC_ACCESS,
            "refreshToken": SYNTHETIC_REFRESH,
            "accountId": raw_account_id,
        }
    }


def _auth_headers(token: str = SERVICE_TOKEN) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _configure_service_token(monkeypatch: pytest.MonkeyPatch, token: str | None) -> None:
    settings = get_settings().model_copy(update={"service_admin_token": token})
    monkeypatch.setattr(service_token_module, "get_settings", lambda: settings)


async def _import(
    async_client,
    raw_account_id: str,
    email: str,
    *,
    plan_type: str = "plus",
    token: str = SERVICE_TOKEN,
):
    return await async_client.post(
        "/api/v1/pool-accounts/import",
        headers=_auth_headers(token),
        files={
            "auth_json": (
                "synthetic-auth.json",
                json.dumps(_make_auth_json(raw_account_id, email, plan_type)),
                "application/json",
            )
        },
    )


@pytest.mark.asyncio
async def test_service_api_auth_is_separate_and_fail_closed(async_client, monkeypatch, caplog) -> None:
    _configure_service_token(monkeypatch, None)
    caplog.set_level(logging.INFO)

    closed = await async_client.get("/api/v1/pool-accounts")
    assert closed.status_code == 401
    assert closed.json()["error"]["code"] == "service_auth_unavailable"

    _configure_service_token(monkeypatch, SERVICE_TOKEN)
    missing = await async_client.get("/api/v1/pool-accounts")
    invalid = await async_client.get("/api/v1/pool-accounts", headers=_auth_headers("wrong-token"))
    valid = await async_client.get("/api/v1/pool-accounts", headers=_auth_headers())

    assert missing.status_code == invalid.status_code == 401
    assert missing.json()["error"]["code"] == invalid.json()["error"]["code"] == "service_auth_invalid"
    assert valid.status_code == 200
    assert SERVICE_TOKEN not in caplog.text
    assert "wrong-token" not in caplog.text


@pytest.mark.asyncio
async def test_service_api_pauses_and_resumes_process_routing(async_client, monkeypatch) -> None:
    _configure_service_token(monkeypatch, SERVICE_TOKEN)

    missing = await async_client.post("/api/v1/routing/pause")
    assert missing.status_code == 401
    assert routing_pause.is_paused() is False

    paused = await async_client.post("/api/v1/routing/pause", headers=_auth_headers())
    paused_again = await async_client.post("/api/v1/routing/pause", headers=_auth_headers())
    status = await async_client.get("/api/v1/routing/status", headers=_auth_headers())

    expected_paused = {"paused": True, "waitingRequests": 0, "scope": "process"}
    assert paused.status_code == paused_again.status_code == status.status_code == 200
    assert paused.json() == paused_again.json() == status.json() == expected_paused

    resumed = await async_client.post("/api/v1/routing/resume", headers=_auth_headers())
    resumed_again = await async_client.post("/api/v1/routing/resume", headers=_auth_headers())
    expected_resumed = {"paused": False, "waitingRequests": 0, "scope": "process"}
    assert resumed.json() == resumed_again.json() == expected_resumed

    assert await drain_audit_log_tasks(timeout_seconds=1)
    async with SessionLocal() as session:
        rows = (
            await session.execute(select(AuditLog).where(AuditLog.action.in_(("routing_paused", "routing_resumed"))))
        ).scalars()
        audit_rows = list(rows)
    assert [row.action for row in audit_rows].count("routing_paused") == 2
    assert [row.action for row in audit_rows].count("routing_resumed") == 2
    assert all(json.loads(row.details or "{}") == {"waiting_requests": 0} for row in audit_rows)
    assert all(SERVICE_TOKEN not in (row.details or "") for row in audit_rows)


@pytest.mark.asyncio
async def test_paused_proxy_request_stays_pending_until_service_resume(async_client, monkeypatch) -> None:
    _configure_service_token(monkeypatch, SERVICE_TOKEN)
    pause = await async_client.post("/api/v1/routing/pause", headers=_auth_headers())
    assert pause.status_code == 200

    proxy_request = asyncio.create_task(async_client.get("/v1/models"))
    try:
        async with asyncio.timeout(1):
            while True:
                status = await async_client.get("/api/v1/routing/status", headers=_auth_headers())
                if status.json()["waitingRequests"] == 1:
                    break
                await asyncio.sleep(0)

        assert not proxy_request.done()

        resume = await async_client.post("/api/v1/routing/resume", headers=_auth_headers())
        assert resume.status_code == 200
        response = await asyncio.wait_for(proxy_request, timeout=2)
    finally:
        routing_pause.resume()
        if not proxy_request.done():
            proxy_request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await proxy_request

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_service_api_import_list_detail_and_queries_are_credential_free(
    async_client,
    monkeypatch,
    caplog,
) -> None:
    _configure_service_token(monkeypatch, SERVICE_TOKEN)
    caplog.set_level(logging.INFO)
    email = "service-one@example.com"
    account_id = generate_unique_account_id("service-one", email)

    imported = await _import(async_client, "service-one", email)
    assert imported.status_code == 200
    assert imported.json()["accountId"] == account_id
    imported_serialized = json.dumps(imported.json())
    for forbidden in (SYNTHETIC_ACCESS, SYNTHETIC_REFRESH, SYNTHETIC_ID, "accessToken", "refreshToken", "idToken"):
        assert forbidden not in imported_serialized
    assert SYNTHETIC_ACCESS not in caplog.text
    assert SYNTHETIC_REFRESH not in caplog.text

    async with SessionLocal() as session:
        await session.execute(update(Account).where(Account.id == account_id).values(alias="primary"))
        await session.commit()

    listed = await async_client.get("/api/v1/pool-accounts", headers=_auth_headers())
    assert listed.status_code == 200
    assert listed.json()["accounts"] == [
        {
            "accountId": account_id,
            "email": email,
            "alias": "primary",
            "status": "active",
            "paused": False,
            "planType": "plus",
            "createdAt": listed.json()["accounts"][0]["createdAt"],
            "lastRefreshAt": listed.json()["accounts"][0]["lastRefreshAt"],
        }
    ]

    detail = await async_client.get(f"/api/v1/pool-accounts/{account_id}", headers=_auth_headers())
    assert detail.status_code == 200
    assert detail.json() == listed.json()["accounts"][0]
    unknown = await async_client.get("/api/v1/pool-accounts/missing", headers=_auth_headers())
    assert unknown.status_code == 404

    assert (
        await async_client.get(
            "/api/v1/pool-accounts",
            params={"email": email},
            headers=_auth_headers(),
        )
    ).json()["accounts"][0]["accountId"] == account_id
    assert (
        await async_client.get(
            "/api/v1/pool-accounts",
            params={"alias": "primary", "status": "active"},
            headers=_auth_headers(),
        )
    ).json()["accounts"][0]["accountId"] == account_id


@pytest.mark.asyncio
async def test_service_api_cursor_is_bounded_and_invalid_cursor_is_rejected(async_client, monkeypatch) -> None:
    _configure_service_token(monkeypatch, SERVICE_TOKEN)
    for index in range(3):
        response = await _import(async_client, f"page-{index}", f"page-{index}@example.com")
        assert response.status_code == 200

    first = await async_client.get(
        "/api/v1/pool-accounts",
        params={"limit": 1},
        headers=_auth_headers(),
    )
    assert first.status_code == 200
    assert len(first.json()["accounts"]) == 1
    assert first.json()["nextCursor"]

    second = await async_client.get(
        "/api/v1/pool-accounts",
        params={"limit": 1, "cursor": first.json()["nextCursor"]},
        headers=_auth_headers(),
    )
    assert second.status_code == 200
    assert len(second.json()["accounts"]) == 1
    assert second.json()["accounts"][0]["accountId"] != first.json()["accounts"][0]["accountId"]

    invalid = await async_client.get(
        "/api/v1/pool-accounts",
        params={"cursor": "not-a-valid-cursor"},
        headers=_auth_headers(),
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_cursor"
    assert (
        await async_client.get(
            "/api/v1/pool-accounts",
            params={"limit": 201},
            headers=_auth_headers(),
        )
    ).status_code == 422


@pytest.mark.asyncio
async def test_service_api_import_errors_and_conflicts_are_stable(async_client, monkeypatch) -> None:
    _configure_service_token(monkeypatch, SERVICE_TOKEN)
    invalid = await async_client.post(
        "/api/v1/pool-accounts/import",
        headers=_auth_headers(),
        files={"auth_json": ("synthetic-auth.json", "not-json", "application/json")},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_auth_json"

    missing = await async_client.post(
        "/api/v1/pool-accounts/import",
        headers=_auth_headers(),
        content=b"not multipart",
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "invalid_auth_json_upload"

    oversized = await async_client.post(
        "/api/v1/pool-accounts/import",
        headers=_auth_headers(),
        files={"auth_json": ("synthetic-auth.json", b"x" * (1024 * 1024 + 1), "application/json")},
    )
    assert oversized.status_code == 413
    assert oversized.json()["error"]["code"] == "payload_too_large"

    settings = await async_client.put(
        "/api/settings",
        json={
            "stickyThreadsEnabled": False,
            "preferEarlierResetAccounts": False,
            "importWithoutOverwrite": True,
            "totpRequiredOnLogin": False,
        },
    )
    assert settings.status_code == 200
    first = await _import(async_client, "conflict-base", "conflict-service@example.com")
    second = await _import(async_client, "conflict-base", "conflict-service@example.com")
    assert first.status_code == second.status_code == 200

    settings = await async_client.put(
        "/api/settings",
        json={
            "stickyThreadsEnabled": False,
            "preferEarlierResetAccounts": False,
            "importWithoutOverwrite": False,
            "totpRequiredOnLogin": False,
        },
    )
    assert settings.status_code == 200
    conflict = await _import(async_client, "conflict-new", "conflict-service@example.com")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "duplicate_identity_conflict"


@pytest.mark.asyncio
async def test_service_api_delete_retains_or_explicitly_purges_history(
    async_client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _configure_service_token(monkeypatch, SERVICE_TOKEN)
    monkeypatch.setattr("app.modules.accounts.service.request_account_deletion_run", lambda: None)

    async def _no_tick(self) -> None:
        return None

    monkeypatch.setattr("app.modules.accounts.deletion.AccountDeletionScheduler._run_once", _no_tick)
    audit_events: list[tuple[str, dict[str, object] | None]] = []

    def capture_audit(action: str, **kwargs: object) -> None:
        details = cast(dict[str, object] | None, kwargs.get("details"))
        audit_events.append((action, details))

    monkeypatch.setattr(service_api_module.AuditService, "log_async", capture_audit)

    retained = await _import(async_client, "retain-history", "retain-history@example.com")
    retained_id = retained.json()["accountId"]
    async with SessionLocal() as session:
        session.add(
            RequestLog(
                account_id=retained_id,
                request_id="synthetic-retained-log",
                model="gpt-5",
                status="200",
            )
        )
        await session.commit()

    deleted = await async_client.delete(
        f"/api/v1/pool-accounts/{retained_id}",
        headers=_auth_headers(),
    )
    assert deleted.status_code == 200
    assert audit_events[-1] == (
        "pool_account_deleted",
        {"account_id": retained_id, "delete_history": False},
    )
    listed = await async_client.get("/api/v1/pool-accounts", headers=_auth_headers())
    assert all(account["accountId"] != retained_id for account in listed.json()["accounts"])
    assert (await async_client.get(f"/api/v1/pool-accounts/{retained_id}", headers=_auth_headers())).status_code == 404

    repeated = await async_client.delete(
        f"/api/v1/pool-accounts/{retained_id}",
        headers=_auth_headers(),
    )
    assert repeated.status_code == 404
    assert repeated.json()["error"]["code"] == "pool_account_not_found"
    assert len(audit_events) == 2

    outcomes = await run_account_deletion_pass()
    assert outcomes[retained_id] == "finalized"
    async with SessionLocal() as session:
        retained_log = (
            await session.execute(select(RequestLog).where(RequestLog.request_id == "synthetic-retained-log"))
        ).scalar_one()
        assert retained_log.account_id is None
        assert retained_log.deleted_at is not None

    purged = await _import(async_client, "purge-history", "purge-history@example.com")
    purged_id = purged.json()["accountId"]
    async with SessionLocal() as session:
        session.add(
            RequestLog(
                account_id=purged_id,
                request_id="synthetic-purged-log",
                model="gpt-5",
                status="200",
            )
        )
        await session.commit()

    purged_response = await async_client.delete(
        f"/api/v1/pool-accounts/{purged_id}?delete_history=true",
        headers=_auth_headers(),
    )
    assert purged_response.status_code == 200
    assert audit_events[-1] == (
        "pool_account_deleted",
        {"account_id": purged_id, "delete_history": True},
    )
    outcomes = await run_account_deletion_pass()
    assert outcomes[purged_id] == "finalized"
    async with SessionLocal() as session:
        assert (
            await session.execute(select(RequestLog).where(RequestLog.request_id == "synthetic-purged-log"))
        ).scalar_one_or_none() is None

    assert all("token" not in json.dumps(details or {}).lower() for _, details in audit_events)
    assert [action for action, _ in audit_events].count("pool_account_imported") == 2
