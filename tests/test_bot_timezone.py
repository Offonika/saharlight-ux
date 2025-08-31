"""Tests for bot timezone configuration."""

from __future__ import annotations

import importlib
import sys
from zoneinfo import ZoneInfo

import pytest


def _run_bot(monkeypatch: pytest.MonkeyPatch) -> tuple[ZoneInfo, ZoneInfo]:
    """Import ``bot.main`` and return scheduler and app timezones."""

    bot = importlib.import_module("services.bot.main")
    monkeypatch.setattr(bot.settings, "telegram_token", "token")
    monkeypatch.setattr(bot.settings, "admin_id", 1, raising=False)
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")
    monkeypatch.setattr(bot, "init_db", lambda: None)

    class DummyJobQueue:
        class _Scheduler:
            def __init__(self) -> None:
                self.timezone: ZoneInfo | None = None
                self.running = False

            def configure(self, *, timezone: ZoneInfo) -> None:  # noqa: D401
                self.timezone = timezone

        def __init__(self) -> None:
            self.scheduler = self._Scheduler()

        def run_once(self, *args: object, **kwargs: object) -> None:
            return None

        def get_jobs_by_name(self, name: str) -> list[object]:  # pragma: no cover - compat
            return []

        def run_repeating(self, *args: object, **kwargs: object) -> None:  # pragma: no cover
            return None

        def jobs(self) -> list[object]:  # pragma: no cover - compat
            return []

    class DummyBot:
        def set_my_commands(self, commands: list[tuple[str, str]]) -> None:  # pragma: no cover
            return None

    class DummyApp:
        def __init__(self) -> None:
            self.bot = DummyBot()
            self.job_queue = DummyJobQueue()
            self.timezone: ZoneInfo | None = None

        def add_error_handler(self, *args: object, **kwargs: object) -> None:
            return None

        def add_handler(self, *args: object, **kwargs: object) -> None:  # pragma: no cover
            return None

        def run_polling(self) -> None:  # pragma: no cover - compat
            return None

    built_app = DummyApp()

    class DummyBuilder:
        def __init__(self) -> None:
            self._tz: ZoneInfo | None = None

        def token(self, _: str) -> "DummyBuilder":
            return self

        def post_init(self, _: object) -> "DummyBuilder":
            return self

        def timezone(self, tz: ZoneInfo) -> "DummyBuilder":
            self._tz = tz
            return self

        def build(self) -> DummyApp:
            built_app.timezone = self._tz
            return built_app

    class DummyApplication:
        @staticmethod
        def builder() -> DummyBuilder:
            return DummyBuilder()

        def __class_getitem__(cls, _: object) -> type["DummyApplication"]:  # pragma: no cover
            return cls

    monkeypatch.setattr(bot, "Application", DummyApplication)
    monkeypatch.setattr(bot, "register_handlers", lambda app: None, raising=False)

    bot.main()

    assert built_app.job_queue.scheduler.timezone is not None
    assert built_app.timezone is not None
    return built_app.job_queue.scheduler.timezone, built_app.timezone


def test_timezone_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Default timezone is UTC when ``BOT_TZ`` is unset."""

    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.delenv("BOT_TZ", raising=False)
    for mod in ["services.api.app.config", "services.bot.main"]:
        sys.modules.pop(mod, None)

    sched_tz, app_tz = _run_bot(monkeypatch)

    assert sched_tz == ZoneInfo("UTC")
    assert app_tz == ZoneInfo("UTC")


def test_timezone_custom(monkeypatch: pytest.MonkeyPatch) -> None:
    """Custom timezone from ``BOT_TZ`` is respected."""

    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.setenv("BOT_TZ", "Asia/Tokyo")
    for mod in ["services.api.app.config", "services.bot.main"]:
        sys.modules.pop(mod, None)

    sched_tz, app_tz = _run_bot(monkeypatch)

    tokyo = ZoneInfo("Asia/Tokyo")
    assert sched_tz == tokyo
    assert app_tz == tokyo

