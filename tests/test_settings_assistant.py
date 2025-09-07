import pytest

from services.api.app.config import Settings


def test_assistant_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings should use defaults for assistant-related variables."""

    monkeypatch.delenv("ASSISTANT_MODE_ENABLED", raising=False)
    monkeypatch.delenv("LEARNING_PLANNER_MODEL", raising=False)
    monkeypatch.delenv("ASSISTANT_MAX_TURNS", raising=False)
    monkeypatch.delenv("ASSISTANT_SUMMARY_TRIGGER", raising=False)
    monkeypatch.delenv("LEARNING_PROMPT_CACHE_TTL_SEC", raising=False)
    settings = Settings(_env_file=None)
    assert settings.assistant_mode_enabled is True
    assert settings.learning_planner_model == "gpt-4o-mini"
    assert settings.assistant_max_turns == 16
    assert settings.assistant_summary_trigger == 12
    assert settings.learning_prompt_cache_ttl_sec == 28800


def test_assistant_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variables should override assistant defaults."""

    monkeypatch.setenv("ASSISTANT_MODE_ENABLED", "0")
    monkeypatch.setenv("LEARNING_PLANNER_MODEL", "gpt-4o")
    monkeypatch.setenv("ASSISTANT_MAX_TURNS", "5")
    monkeypatch.setenv("ASSISTANT_SUMMARY_TRIGGER", "7")
    monkeypatch.setenv("LEARNING_PROMPT_CACHE_TTL_SEC", "42")
    settings = Settings(_env_file=None)
    assert settings.assistant_mode_enabled is False
    assert settings.learning_planner_model == "gpt-4o"
    assert settings.assistant_max_turns == 5
    assert settings.assistant_summary_trigger == 7
    assert settings.learning_prompt_cache_ttl_sec == 42
