"""Ensure only a single test reminder is scheduled on startup."""

from __future__ import annotations

import importlib
import sys

import pytest
from zoneinfo import ZoneInfo


def test_single_test_reminder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Bot starts with only one scheduled test job."""

    monkeypatch.setenv("DB_PASSWORD", "pwd")
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("TELEGRAM_TOKEN", "token")

    for mod in ["services.api.app.config", "services.bot.main"]:
        sys.modules.pop(mod, None)
    bot = importlib.import_module("services.bot.main")
    monkeypatch.setattr(bot.settings, "telegram_token", "token")
    monkeypatch.setattr(bot.settings, "admin_id", 1, raising=False)
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")
    monkeypatch.setattr(bot, "init_db", lambda: None)
    monkeypatch.setattr(bot, "build_persistence", lambda: object())

    class DummyJobQueue:
        class _Scheduler:
            def __init__(self) -> None:
                self.timezone: object | None = None

            def configure(self, *, timezone: object) -> None:
                self.timezone = timezone

        def __init__(self) -> None:
            self.calls = 0
            self.scheduler = self._Scheduler()

        def run_once(self, *args: object, **kwargs: object) -> None:
            self.calls += 1

        def get_jobs_by_name(
            self, name: str
        ) -> list[object]:  # pragma: no cover - compatibility
            return []

        def run_repeating(
            self, *args: object, **kwargs: object
        ) -> None:  # pragma: no cover - compatibility
            return None

        def jobs(self) -> list[object]:  # pragma: no cover - compatibility
            return []

    class DummyBot:
        def set_my_commands(
            self, commands: list[tuple[str, str]]
        ) -> None:  # pragma: no cover - compatibility
            return None

    class DummyApp:
        def __init__(self) -> None:
            self.bot = DummyBot()
            self.job_queue = DummyJobQueue()
            self.timezone = ZoneInfo("UTC")

        def add_error_handler(
            self, handler: object
        ) -> None:  # pragma: no cover - compatibility
            return None

        def add_handler(
            self, handler: object, *, group: int | None = None
        ) -> None:  # pragma: no cover - compatibility
            return None

        def run_polling(self) -> None:  # pragma: no cover - compatibility
            return None

    built_app = DummyApp()

    class DummyBuilder:
        def token(self, _: str) -> "DummyBuilder":
            return self

        def persistence(self, _: object) -> "DummyBuilder":
            return self

        def post_init(self, _: object) -> "DummyBuilder":
            return self

        def build(self) -> DummyApp:
            return built_app

    class DummyApplication:
        @staticmethod
        def builder() -> DummyBuilder:
            return DummyBuilder()

        def __class_getitem__(
            cls, _: object
        ) -> type["DummyApplication"]:  # pragma: no cover - typing helper
            return cls

    monkeypatch.setattr(bot, "Application", DummyApplication)
    monkeypatch.setattr(bot, "register_handlers", lambda app: None, raising=False)

    bot.main()

    assert built_app.job_queue.calls == 1
