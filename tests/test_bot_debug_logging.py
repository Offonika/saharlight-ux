"""Tests for debug logging configuration in bot.main."""

from __future__ import annotations

import importlib
import logging
import sys
from typing import Awaitable, Callable
from zoneinfo import ZoneInfo

import pytest
from telegram.ext import ContextTypes


def test_log_level_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    """Setting LOG_LEVEL=DEBUG enables debug logging in bot.main."""

    # Prepare environment for config module
    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")

    # Ensure fresh imports so that env vars are read
    for mod in ["services.api.app.config", "services.bot.main"]:
        sys.modules.pop(mod, None)
    bot = importlib.import_module("services.bot.main")
    monkeypatch.setattr(bot.settings, "telegram_token", "token")
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")

    # Stub external interactions
    monkeypatch.setattr(bot, "init_db", lambda: None)
    monkeypatch.setattr(bot, "build_persistence", lambda: object())

    class DummyJobQueue:
        class _Scheduler:
            def __init__(self) -> None:
                self.timezone: object | None = None

            def configure(self, *, timezone: object) -> None:
                self.timezone = timezone

        scheduler = _Scheduler()

        def run_once(self, *args: object, **kwargs: object) -> None:
            return None

        def get_jobs_by_name(self, name: str) -> list[object]:
            return []

        def run_repeating(self, *args: object, **kwargs: object) -> None:
            return None

        def jobs(self) -> list[object]:
            return []

    class DummyBot:
        def set_my_commands(self, commands: list[tuple[str, str]]) -> None:
            return None

    class DummyApp:
        bot = DummyBot()
        job_queue = DummyJobQueue()
        timezone = ZoneInfo("UTC")

        def add_error_handler(
            self,
            handler: Callable[[object, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
        ) -> None:
            return None

        def add_handler(
            self, handler: object, *, group: int | None = None
        ) -> None:  # pragma: no cover - compatibility
            return None

        def run_polling(self) -> None:
            return None

    class DummyBuilder:
        def token(self, _: str) -> "DummyBuilder":
            return self

        def persistence(self, _: object) -> "DummyBuilder":
            return self

        def post_init(self, _: object) -> "DummyBuilder":
            return self

        def build(self) -> DummyApp:
            return DummyApp()

    class DummyApplication:
        @staticmethod
        def builder() -> DummyBuilder:
            return DummyBuilder()

        def __class_getitem__(
            cls, _: object
        ) -> type[DummyApplication]:  # Support subscripting in type hints
            return cls

    monkeypatch.setattr(bot, "Application", DummyApplication)
    monkeypatch.setattr(bot, "register_handlers", lambda app: None, raising=False)

    # Reset and capture logging configuration
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers.clear()

    try:
        bot.main()
        assert root.level == logging.DEBUG
    finally:
        root.handlers[:] = previous_handlers
        root.setLevel(previous_level)
