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


def test_webhook_ips_empty(monkeypatch) -> None:
    monkeypatch.delenv("BILLING_WEBHOOK_IPS", raising=False)
    settings = BillingSettings(_env_file=None)
    assert settings.billing_webhook_ips == []


def test_webhook_ips_parsing(monkeypatch) -> None:
    monkeypatch.setenv("BILLING_WEBHOOK_IPS", "1.2.3.4,5.6.7.8")
    settings = BillingSettings()
    assert settings.billing_webhook_ips == ["1.2.3.4", "5.6.7.8"]
