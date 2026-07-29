from __future__ import annotations

from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from app.core.auth import service_token
from app.core.config.settings import Settings

pytestmark = pytest.mark.unit


def test_service_token_configuration_is_optional_but_rejects_blank_and_weak_values() -> None:
    assert Settings(_env_file=None).service_admin_token is None
    with pytest.raises(ValidationError, match="must not be blank"):
        Settings(_env_file=None, service_admin_token="   ")
    with pytest.raises(ValidationError, match="at least 32 characters"):
        Settings(_env_file=None, service_admin_token="short")
    assert Settings(_env_file=None, service_admin_token="s" * 32).service_admin_token == "s" * 32


def test_service_token_comparison_uses_constant_time_primitive(monkeypatch: pytest.MonkeyPatch) -> None:
    compare_digest = Mock(return_value=True)
    monkeypatch.setattr(service_token.secrets, "compare_digest", compare_digest)

    assert service_token._service_token_matches("presented", "configured") is True
    compare_digest.assert_called_once()
    presented_digest, configured_digest = compare_digest.call_args.args
    assert len(presented_digest) == len(configured_digest) == 32
