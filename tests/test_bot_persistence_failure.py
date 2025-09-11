from __future__ import annotations

import importlib
import logging
import sys

import pytest


def test_persistence_failure_exits(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """main() exits with non-zero code if persistence cannot be built."""

    monkeypatch.setenv("DB_PASSWORD", "pwd")
    for mod in ["services.api.app.config", "services.bot.main"]:
        sys.modules.pop(mod, None)
    bot = importlib.import_module("services.bot.main")
    monkeypatch.setattr(bot.settings, "telegram_token", "token")
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")
    monkeypatch.setattr(bot, "init_db", lambda: None)

    def failing_build_persistence() -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(bot, "build_persistence", failing_build_persistence)

    with caplog.at_level(logging.ERROR), pytest.raises(SystemExit) as excinfo:
        bot.main()

    assert excinfo.value.code != 0
    assert any("STATE_DIRECTORY" in message for message in caplog.messages)
