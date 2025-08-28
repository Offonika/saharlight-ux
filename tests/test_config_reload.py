import pytest

import services.api.app.config as config


def test_reload_settings_reflects_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    config.reload_settings()
    assert config.get_settings().public_origin == ""

    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    config.reload_settings()
    assert config.get_settings().public_origin == "https://example.com"

    monkeypatch.delenv("PUBLIC_ORIGIN", raising=False)
    config.reload_settings()
