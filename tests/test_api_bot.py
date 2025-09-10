"""Tests for services.api.app.bot."""

from __future__ import annotations

import importlib
import logging
import sys
from pathlib import Path

import pytest


def test_main_attaches_onboarding_handler_and_runs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """main builds Application with token and runs polling."""

    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("UI_BASE_URL", "https://ui")
    monkeypatch.setenv("BOT_PERSISTENCE_PATH", str(tmp_path / "data.pkl"))

    sys.modules.pop("services.api.app.bot", None)
    bot = importlib.import_module("services.api.app.bot")

    sentinel_handler = object()
    captured: dict[str, str] = {}

    def fake_build_start_handler(url: str) -> object:
        captured["url"] = url
        return sentinel_handler

    monkeypatch.setattr(bot, "build_start_handler", fake_build_start_handler)

    class DummyApp:
        def __init__(self) -> None:
            self.handlers: list[object] = []
            self.run_polling_called = False

        def add_handler(self, handler: object) -> None:
            self.handlers.append(handler)

        def run_polling(self) -> None:
            self.run_polling_called = True

    built_app = DummyApp()

    class DummyBuilder:
        def __init__(self) -> None:
            self.token_value: str | None = None
            self.persistence_obj: object | None = None

        def token(self, value: str) -> "DummyBuilder":
            self.token_value = value
            return self

        def persistence(self, obj: object) -> "DummyBuilder":
            self.persistence_obj = obj
            return self

        def build(self) -> DummyApp:
            return built_app

    dummy_builder = DummyBuilder()

    class DummyApplication:
        @staticmethod
        def builder() -> DummyBuilder:
            return dummy_builder

    monkeypatch.setattr(bot, "Application", DummyApplication)

    bot.main()

    assert dummy_builder.token_value == "token"
    assert sentinel_handler in built_app.handlers
    assert built_app.run_polling_called
    assert captured["url"] == "https://ui"


def test_main_fails_without_token(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """main exits with error when TELEGRAM_TOKEN is missing."""

    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.delenv("TELEGRAM_TOKEN", raising=False)

    sys.modules.pop("services.api.app.bot", None)
    bot = importlib.import_module("services.api.app.bot")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError):
            bot.main()

    assert "TELEGRAM_TOKEN" in caplog.text
