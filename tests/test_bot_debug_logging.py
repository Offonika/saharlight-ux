"""Tests for debug logging configuration in bot.main."""

import importlib
import logging
import sys
import asyncio


def test_log_level_debug(monkeypatch):
    """Setting LOG_LEVEL=DEBUG enables debug logging in bot.main."""

    # Prepare environment for config module
    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")

    # Ensure fresh imports so that env vars are read
    for mod in ["diabetes.config", "bot"]:
        sys.modules.pop(mod, None)
    bot = importlib.import_module("bot")

    # Stub external interactions
    monkeypatch.setattr(bot, "init_db", lambda: None)

    class DummyBot:
        async def set_my_commands(self, commands):
            return None

    class DummyUpdater:
        async def start_polling(self):
            return None

        async def idle(self):
            return None

    class DummyApp:
        bot = DummyBot()
        updater = DummyUpdater()

        async def initialize(self):
            return None

        async def start(self):
            return None

        async def stop(self):
            return None

        async def shutdown(self):
            return None

    class DummyBuilder:
        def token(self, _):
            return self

        def build(self):
            return DummyApp()

    class DummyApplication:
        @staticmethod
        def builder():
            return DummyBuilder()

    monkeypatch.setattr(bot, "Application", DummyApplication)
    monkeypatch.setattr(bot, "register_handlers", lambda app: None)

    # Reset and capture logging configuration
    root = logging.getLogger()
    previous_handlers = root.handlers[:]
    previous_level = root.level
    root.handlers.clear()

    try:
        asyncio.run(bot.main())
        assert root.level == logging.DEBUG
    finally:
        root.handlers[:] = previous_handlers
        root.setLevel(previous_level)

