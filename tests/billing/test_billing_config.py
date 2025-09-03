from __future__ import annotations

import pytest
from pydantic import ValidationError

from services.api.app.billing.config import BillingSettings


def test_dummy_provider_allows_missing_admin_token(monkeypatch) -> None:
    monkeypatch.setenv("BILLING_PROVIDER", "dummy")
    monkeypatch.delenv("BILLING_ADMIN_TOKEN", raising=False)
    settings = BillingSettings()
    assert settings.billing_admin_token is None


def test_real_provider_requires_admin_token(monkeypatch) -> None:
    monkeypatch.setenv("BILLING_PROVIDER", "stripe")
    monkeypatch.delenv("BILLING_ADMIN_TOKEN", raising=False)
    with pytest.raises(ValidationError):
        BillingSettings()
