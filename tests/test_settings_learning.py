from __future__ import annotations

import pytest

from services.api.app.config import Settings


def test_learning_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should use built-in defaults for learning variables."""

    monkeypatch.delenv("LEARNING_MODE_ENABLED", raising=False)
    monkeypatch.delenv("LEARNING_ENABLED", raising=False)
    monkeypatch.delenv("LEARNING_ASSISTANT_ID", raising=False)
    monkeypatch.delenv("LEARNING_COMMAND_MODEL", raising=False)
    monkeypatch.delenv("LEARNING_CONTENT_MODE", raising=False)
    settings = Settings(_env_file=None)
    assert settings.learning_mode_enabled is True
    assert settings.learning_assistant_id is None
    assert settings.learning_command_model == "gpt-4o-mini"
    assert settings.learning_content_mode == "dynamic"


def test_learning_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables should override learning defaults."""

    monkeypatch.setenv("LEARNING_MODE_ENABLED", "0")
    monkeypatch.setenv("LEARNING_ASSISTANT_ID", "abc")
    monkeypatch.setenv("LEARNING_COMMAND_MODEL", "gpt-4o")
    monkeypatch.setenv("LEARNING_CONTENT_MODE", "static")
    settings = Settings(_env_file=None)
    assert settings.learning_mode_enabled is False
    assert settings.learning_assistant_id == "abc"
    assert settings.learning_command_model == "gpt-4o"
    assert settings.learning_content_mode == "static"
