"""Billing configuration via Pydantic settings."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Any

from pydantic import Field, IPvAnyAddress, field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)


class CommaSeparatedEnvSettingsSource(EnvSettingsSource):
    def decode_complex_value(
        self, field_name: str, field: Any, value: str
    ) -> str:
        return value


class BillingSettings(BaseSettings):
    """Runtime billing configuration."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            CommaSeparatedEnvSettingsSource(settings_cls),
            dotenv_settings,
            file_secret_settings,
        )

    billing_enabled: bool = Field(default=False, alias="BILLING_ENABLED")
    billing_test_mode: bool = Field(default=True, alias="BILLING_TEST_MODE")
    billing_provider: str = Field(default="dummy", alias="BILLING_PROVIDER")
    paywall_mode: str = Field(default="soft", alias="PAYWALL_MODE")
    billing_admin_token: str | None = Field(default=None, alias="BILLING_ADMIN_TOKEN")
    billing_webhook_secret: str | None = Field(
        default=None, alias="BILLING_WEBHOOK_SECRET"
    )
    billing_webhook_ips: list[IPvAnyAddress] = Field(
        default_factory=list, alias="BILLING_WEBHOOK_IPS"
    )
    billing_webhook_timeout: float = Field(default=5.0, alias="BILLING_WEBHOOK_TIMEOUT")

    @model_validator(mode="after")
    def _require_admin_token(self) -> "BillingSettings":
        """Ensure real providers have an admin token configured."""
        if self.billing_provider != "dummy" and not self.billing_admin_token:
            raise ValueError("BILLING_ADMIN_TOKEN is required for non-dummy providers")
        return self

    @field_validator("billing_webhook_ips", mode="before")
    @classmethod
    def _parse_webhook_ips(
        cls, value: str | list[str] | list[IPvAnyAddress]
    ) -> list[IPvAnyAddress]:
        """Split comma-separated IPs and parse each entry."""
        if isinstance(value, str):
            value = [v.strip() for v in value.split(",") if v.strip()]
        return [ip_address(v) for v in value]


billing_settings = BillingSettings()


def get_billing_settings() -> BillingSettings:
    """Return current billing settings."""

    return billing_settings


def reload_billing_settings() -> BillingSettings:
    """Reload billing settings from the environment."""

    global billing_settings
    billing_settings = BillingSettings()
    return billing_settings
