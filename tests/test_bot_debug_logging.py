"""Tests for debug logging configuration in bot.main."""

import importlib
import logging
import sys


def test_log_level_debug(monkeypatch):
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
        def set_my_commands(self, commands):
            return None

    class DummyApp:
        bot = DummyBot()
        job_queue = None

        def add_error_handler(self, _):
            return None

        def add_handler(self, _):
            return None

        def run_polling(self):
            return None

    class DummyBuilder:
        def token(self, _):
            return self

        def post_init(self, _):
            return self

        def build(self):
            return DummyApp()

    class DummyApplication:
        @staticmethod
        def builder():
            return DummyBuilder()

        def __class_getitem__(cls, _):  # Support subscripting in type hints
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

