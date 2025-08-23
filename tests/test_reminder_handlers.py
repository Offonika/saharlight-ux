import json
from types import TracebackType
from typing import Any
from unittest.mock import MagicMock

import importlib
import pytest
from telegram import Update, User
from telegram.ext import CallbackContext

from services.api.app.diabetes.utils.helpers import INVALID_TIME_MSG


@pytest.fixture
def reminder_handlers(monkeypatch: pytest.MonkeyPatch) -> Any:
    monkeypatch.setenv("WEBAPP_URL", "https://example.com")
    import services.api.app.config as config
    import services.api.app.diabetes.handlers.reminder_handlers as reminder_handlers
    importlib.reload(config)
    importlib.reload(reminder_handlers)
    yield reminder_handlers
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    importlib.reload(config)
    importlib.reload(reminder_handlers)


@pytest.fixture
def settings(reminder_handlers: Any) -> Any:  # noqa: ANN401
    import services.api.app.config as config
    return config.settings


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


class DummyWebAppData:
    def __init__(self, data: str) -> None:
        self.data = data


class DummyWebAppMessage(DummyMessage):
    def __init__(self, data: str) -> None:
        super().__init__()
        self.web_app_data = DummyWebAppData(data)


def make_user(user_id: int) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    return user


def make_update(**kwargs: Any) -> MagicMock:
    update = MagicMock(spec=Update)
    for key, value in kwargs.items():
        setattr(update, key, value)
    return update


def make_context(**kwargs: Any) -> MagicMock:
    context = MagicMock(spec=CallbackContext)
    for key, value in kwargs.items():
        setattr(context, key, value)
    return context


@pytest.mark.asyncio
async def test_add_reminder_fewer_args(reminder_handlers: Any) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar"])

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Использование: /addreminder <type> <value>"]


@pytest.mark.asyncio
async def test_add_reminder_sugar_invalid_time(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "ab:cd"])

    parse_mock = MagicMock(side_effect=ValueError)
    monkeypatch.setattr(reminder_handlers, "parse_time_interval", parse_mock)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == [INVALID_TIME_MSG]
    parse_mock.assert_called_once_with("ab:cd")


@pytest.mark.asyncio
async def test_add_reminder_sugar_non_numeric_interval(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "abc"])

    parse_mock = MagicMock()
    monkeypatch.setattr(reminder_handlers, "parse_time_interval", parse_mock)

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Интервал должен быть числом."]
    parse_mock.assert_not_called()


@pytest.mark.asyncio
async def test_add_reminder_unknown_type(reminder_handlers: Any) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["unknown", "1"])

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Неизвестный тип напоминания."]


@pytest.mark.asyncio
async def test_add_reminder_valid_type(
    reminder_handlers: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    message = DummyMessage()
    update = make_update(message=message, effective_user=make_user(1))
    context = make_context(args=["sugar", "2"], job_queue=None)
    class DummyQuery:
        def filter_by(self, **kwargs: Any) -> "DummyQuery":
            return self

        def count(self) -> int:
            return 0

    class DummySession:
        def __enter__(self) -> "DummySession":
            return self

        def __exit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: TracebackType | None,
        ) -> None:
            pass

        def query(self, *args: Any, **kwargs: Any) -> DummyQuery:
            return DummyQuery()

        def get(self, *args: Any, **kwargs: Any) -> Any:
            return None

        def add(self, obj: Any) -> None:
            pass

    def session_factory() -> DummySession:
        return DummySession()

    monkeypatch.setattr(reminder_handlers, "run_db", None)
    monkeypatch.setattr(reminder_handlers, "SessionLocal", session_factory)
    monkeypatch.setattr(reminder_handlers, "commit", lambda s: True)
    monkeypatch.setattr(reminder_handlers, "_describe", lambda *a, **k: "desc")

    await reminder_handlers.add_reminder(update, context)

    assert message.texts == ["Сохранено: desc"]


@pytest.mark.asyncio
async def test_reminder_webapp_save_unknown_type(
    reminder_handlers: Any
) -> None:
    message = DummyWebAppMessage(json.dumps({"type": "bad", "value": "10:00"}))
    update = make_update(effective_message=message, effective_user=make_user(1))
    context = make_context()

    await reminder_handlers.reminder_webapp_save(update, context)

    assert message.texts == ["Неизвестный тип напоминания."]


@pytest.mark.parametrize(
    "base_url",
    [
        "https://example.com",
        "https://example.com/",
        "https://example.com/ui",
        "https://example.com/ui/",
    ],
)
def test_build_webapp_url(
    reminder_handlers: Any, settings: Any, monkeypatch: pytest.MonkeyPatch, base_url: str
) -> None:
    monkeypatch.setattr(settings, "webapp_url", base_url)
    url = reminder_handlers.build_webapp_url("/ui/reminders")
    assert url == "https://example.com/ui/reminders"
    assert "//" not in url.split("://", 1)[1]


def test_build_webapp_url_without_base(
    reminder_handlers: Any, settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = "/ui/reminders"
    monkeypatch.setattr(settings, "webapp_url", "")
    with pytest.raises(RuntimeError, match="WEBAPP_URL not configured"):
        reminder_handlers.build_webapp_url(path)
