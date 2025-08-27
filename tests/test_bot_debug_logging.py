"""Tests for debug logging configuration in bot.main."""

import importlib
import logging
import sys
from typing import Any


def test_log_level_debug(monkeypatch: Any) -> None:
    """Setting LOG_LEVEL=DEBUG enables debug logging in bot.main."""

    # Prepare environment for config module
    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # Ensure fresh imports so that env vars are read
    for mod in ["services.api.app.config", "services.bot.main"]:
        sys.modules.pop(mod, None)
    bot = importlib.import_module("services.bot.main")

    # Stub external interactions
    monkeypatch.setattr(bot, "init_db", lambda: None)

    class DummyBot:
        def set_my_commands(self, commands: list[tuple[str, str]]) -> None:
            return None

    class DummyApp:
        bot = DummyBot()
        job_queue = None

        def add_error_handler(self, _: object) -> None:
            return None

        def add_handler(self, _: object) -> None:
            return None

        def run_polling(self) -> None:
            return None

    class DummyBuilder:
        def token(self, _: str) -> None:
            return self

        def post_init(self, _: object) -> None:
            return self

        def build(self) -> None:
            return DummyApp()

    class DummyApplication:
        @staticmethod
        def builder() -> None:
            return DummyBuilder()

        def __class_getitem__(cls, _: object) -> None:  # Support subscripting in type hints
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

