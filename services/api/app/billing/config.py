"""Billing configuration via Pydantic settings."""

from __future__ import annotations

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BillingSettings(BaseSettings):
    """Runtime billing configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    billing_enabled: bool = Field(default=False, alias="BILLING_ENABLED")
    billing_test_mode: bool = Field(default=True, alias="BILLING_TEST_MODE")
    billing_provider: str = Field(default="dummy", alias="BILLING_PROVIDER")
    paywall_mode: str = Field(default="soft", alias="PAYWALL_MODE")
    billing_admin_token: str | None = Field(
        default=None, alias="BILLING_ADMIN_TOKEN"
    )
    billing_webhook_secret: str | None = Field(
        default=None, alias="BILLING_WEBHOOK_SECRET"
    )
    billing_webhook_ips: list[str] = Field(
        default_factory=list, alias="BILLING_WEBHOOK_IPS"
    )
    billing_webhook_timeout: float = Field(
        default=5.0, alias="BILLING_WEBHOOK_TIMEOUT"
    )

    @model_validator(mode="after")
    def _require_admin_token(self) -> "BillingSettings":
        """Ensure real providers have an admin token configured."""
        if self.billing_provider != "dummy" and not self.billing_admin_token:
            raise ValueError("BILLING_ADMIN_TOKEN is required for non-dummy providers")
        return self

    @field_validator("billing_webhook_ips", mode="before")
    @classmethod
    def _split_ips(cls, v: str | list[str]) -> list[str]:
        """Split comma-separated IP list from env."""
        if isinstance(v, str):
            return [ip.strip() for ip in v.split(",") if ip.strip()]
        return v


billing_settings = BillingSettings()


def get_billing_settings() -> BillingSettings:
    """Return current billing settings."""

    return billing_settings


def reload_billing_settings() -> BillingSettings:
    """Reload billing settings from the environment."""

    global billing_settings
    billing_settings = BillingSettings()
    return billing_settings
