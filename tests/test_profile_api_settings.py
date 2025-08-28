import sys
import types

import pytest

from services.api.app import config
from services.api.app.config import Settings
from services.api.app.diabetes.handlers.profile.api import get_api


def _setup_sdk(monkeypatch: pytest.MonkeyPatch) -> tuple[type, type, type]:
    """Install dummy ``diabetes_sdk`` modules for testing."""

    sdk = types.ModuleType("diabetes_sdk")
    api_pkg = types.ModuleType("diabetes_sdk.api")
    default_api_mod = types.ModuleType("diabetes_sdk.api.default_api")
    client_mod = types.ModuleType("diabetes_sdk.api_client")
    conf_mod = types.ModuleType("diabetes_sdk.configuration")
    exc_mod = types.ModuleType("diabetes_sdk.exceptions")
    models_pkg = types.ModuleType("diabetes_sdk.models")
    profile_mod = types.ModuleType("diabetes_sdk.models.profile")

    sdk.api = api_pkg
    api_pkg.default_api = default_api_mod
    sdk.api_client = client_mod
    sdk.configuration = conf_mod
    sdk.exceptions = exc_mod
    sdk.models = models_pkg
    models_pkg.profile = profile_mod

    monkeypatch.setitem(sys.modules, "diabetes_sdk", sdk)
    monkeypatch.setitem(sys.modules, "diabetes_sdk.api", api_pkg)
    monkeypatch.setitem(sys.modules, "diabetes_sdk.api.default_api", default_api_mod)
    monkeypatch.setitem(sys.modules, "diabetes_sdk.api_client", client_mod)
    monkeypatch.setitem(sys.modules, "diabetes_sdk.configuration", conf_mod)
    monkeypatch.setitem(sys.modules, "diabetes_sdk.exceptions", exc_mod)
    monkeypatch.setitem(sys.modules, "diabetes_sdk.models", models_pkg)
    monkeypatch.setitem(sys.modules, "diabetes_sdk.models.profile", profile_mod)

    class DummyApi:
        def __init__(self, client: object) -> None:
            self.client = client

    class DummyClient:
        def __init__(self, cfg: object) -> None:
            self.configuration = cfg

    class DummyConfig:
        def __init__(self, host: str | None = None) -> None:
            self.host = host

    class DummyExc(Exception):
        pass

    class DummyProfile:  # pragma: no cover - simple placeholder
        pass

    default_api_mod.DefaultApi = DummyApi
    client_mod.ApiClient = DummyClient
    conf_mod.Configuration = DummyConfig
    exc_mod.ApiException = DummyExc
    profile_mod.Profile = DummyProfile

    return DummyApi, DummyExc, DummyProfile


def test_get_api_accepts_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    DummyApi, DummyExc, DummyProfile = _setup_sdk(monkeypatch)

    custom = Settings(API_URL="http://example.org")
    api, exc, model = get_api(settings=custom)

    assert isinstance(api, DummyApi)
    assert exc is DummyExc
    assert model is DummyProfile
    assert api.client.configuration.host == "http://example.org"


def test_get_api_uses_config_get_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    DummyApi, _, _ = _setup_sdk(monkeypatch)

    called: list[None] = []

    def fake_get_settings() -> Settings:
        called.append(None)
        return Settings(API_URL="http://test.local")

    monkeypatch.setattr(config, "get_settings", fake_get_settings)

    api, _, _ = get_api()

    assert called
    assert isinstance(api, DummyApi)
    assert api.client.configuration.host == "http://test.local"
