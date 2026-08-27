from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.audit.service import AuditService
from app.core.auth.dependencies import set_dashboard_error_format
from app.core.auth.service_token import validate_service_admin_token
from app.core.exceptions import (
    DashboardBadRequestError,
    DashboardConflictError,
    DashboardNotFoundError,
)
from app.core.middleware.multipart_content_encoding import raise_for_unsupported_multipart_content_encoding
from app.core.multipart import ACCOUNT_IMPORT_MULTIPART_POLICY, bounded_multipart_form, read_bounded_upload
from app.core.multipart_fields import required_upload
from app.db.models import AccountStatus
from app.dependencies import AccountsContext, get_accounts_context
from app.modules.accounts.repository import AccountIdentityConflictError
from app.modules.accounts.schemas import (
    AccountDeleteResponse,
    AccountImportResponse,
    PoolAccountResponse,
    PoolAccountsResponse,
)
from app.modules.accounts.service import InvalidAuthJsonError, InvalidPoolAccountCursorError

router = APIRouter(
    prefix="/api/v1/pool-accounts",
    tags=["service-api"],
    dependencies=[Depends(set_dashboard_error_format), Depends(validate_service_admin_token)],
)

_POOL_ACCOUNT_IMPORT_OPENAPI_EXTRA = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "title": "Body_import_pool_account_api_v1_pool_accounts_import_post",
                    "required": ["auth_json"],
                    "properties": {
                        "auth_json": {
                            "type": "string",
                            "contentMediaType": "application/octet-stream",
                            "title": "Auth Json",
                        }
                    },
                }
            }
        },
    }
}


@router.get("", response_model=PoolAccountsResponse)
async def list_pool_accounts(
    email: str | None = Query(default=None),
    status: AccountStatus | None = Query(default=None),
    alias: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    context: AccountsContext = Depends(get_accounts_context),
) -> PoolAccountsResponse:
    try:
        return await context.service.list_pool_accounts(
            email=email,
            status=status,
            alias=alias,
            limit=limit,
            cursor=cursor,
        )
    except InvalidPoolAccountCursorError as exc:
        raise DashboardBadRequestError("Invalid pool-account cursor", code="invalid_cursor") from exc


@router.get("/{account_id}", response_model=PoolAccountResponse)
async def get_pool_account(
    account_id: str,
    context: AccountsContext = Depends(get_accounts_context),
) -> PoolAccountResponse:
    account = await context.service.get_pool_account(account_id)
    if account is None:
        raise DashboardNotFoundError("Pool account not found", code="pool_account_not_found")
    return account


async def _read_pool_account_auth_json(request: Request) -> bytes:
    raise_for_unsupported_multipart_content_encoding(request)
    try:
        async with bounded_multipart_form(
            request,
            ACCOUNT_IMPORT_MULTIPART_POLICY,
            typed_upload_fields=("auth_json",),
        ) as form:
            auth_json = required_upload(form, "auth_json")
            return await read_bounded_upload(
                auth_json,
                max_bytes=ACCOUNT_IMPORT_MULTIPART_POLICY.max_file_bytes,
                param="auth_json",
            )
    except RequestValidationError as exc:
        raise DashboardBadRequestError("auth_json upload is required", code="invalid_auth_json_upload") from exc
    except StarletteHTTPException as exc:
        raise DashboardBadRequestError("Invalid multipart auth_json upload", code="invalid_auth_json_upload") from exc


@router.post(
    "/import",
    response_model=AccountImportResponse,
    openapi_extra=_POOL_ACCOUNT_IMPORT_OPENAPI_EXTRA,
)
async def import_pool_account(
    request: Request,
    context: AccountsContext = Depends(get_accounts_context),
) -> AccountImportResponse:
    raw = await _read_pool_account_auth_json(request)
    try:
        response = await context.service.import_account(raw)
    except InvalidAuthJsonError as exc:
        raise DashboardBadRequestError("Invalid auth.json payload", code="invalid_auth_json") from exc
    except AccountIdentityConflictError as exc:
        raise DashboardConflictError(str(exc), code="duplicate_identity_conflict") from exc

    AuditService.log_async(
        "pool_account_imported",
        actor_ip=request.client.host if request.client else None,
        details={
            "account_id": response.account_id,
            "email": response.email,
            "status": response.status,
        },
    )
    return response


@router.delete("/{account_id}", response_model=AccountDeleteResponse)
async def delete_pool_account(
    request: Request,
    account_id: str,
    delete_history: bool = Query(default=False),
    context: AccountsContext = Depends(get_accounts_context),
) -> AccountDeleteResponse:
    if await context.service.get_pool_account(account_id) is None:
        raise DashboardNotFoundError("Pool account not found", code="pool_account_not_found")
    success = await context.service.delete_account(account_id, delete_history=delete_history)
    if not success:
        raise DashboardNotFoundError("Pool account not found", code="pool_account_not_found")

    AuditService.log_async(
        "pool_account_deleted",
        actor_ip=request.client.host if request.client else None,
        details={"account_id": account_id, "delete_history": delete_history},
    )
    return AccountDeleteResponse(status="deleted")
