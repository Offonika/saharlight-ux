"""Tests for services.api.app.bot."""

from __future__ import annotations

import importlib
import sys

import pytest


def test_main_attaches_onboarding_handler_and_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """main builds Application with token and runs polling."""

    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")

    sys.modules.pop("services.api.app.bot", None)
    bot = importlib.import_module("services.api.app.bot")

    sentinel_handler = object()
    monkeypatch.setattr(bot, "onboarding_conv", sentinel_handler)

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

        def token(self, value: str) -> "DummyBuilder":
            self.token_value = value
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
    assert built_app.handlers[0] is sentinel_handler
    assert len(built_app.handlers) >= 1
    assert built_app.run_polling_called
