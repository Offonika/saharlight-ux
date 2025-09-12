from __future__ import annotations

import pytest

from services.api.app.bot import get_api_base_url


def test_uses_api_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://new.example")
    monkeypatch.setenv("API_BASE_URL", "http://old.example")
    assert get_api_base_url() == "http://new.example"


def test_falls_back_to_api_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.setenv("API_BASE_URL", "http://old.example")
    assert get_api_base_url() == "http://old.example"


def test_default_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("API_URL", raising=False)
    monkeypatch.delenv("API_BASE_URL", raising=False)
    assert get_api_base_url() == "/api"
