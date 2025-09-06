import importlib
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from telegram import Update
from telegram.ext import CallbackContext

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.profile.conversation"
)


class DummyMessage:
    def __init__(self, text: str | None = None) -> None:
        self.text = text
        self.replies: list[str] = []
        self.markups: list[Any] = []
        self.web_app_data: Any | None = None

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.markups.append(kwargs.get("reply_markup"))

    async def delete(self) -> None:
        pass


@pytest.mark.asyncio
async def test_profile_timezone_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUBLIC_ORIGIN", "")
    message = DummyMessage()
    query = SimpleNamespace(message=message, answer=AsyncMock())
    update = cast(Update, SimpleNamespace(callback_query=query))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    state = await handlers.profile_timezone(update, context)
    assert state == handlers.PROFILE_TZ
    assert "Введите ваш часовой пояс" in message.replies[0]
    assert any("вручную" in r.lower() for r in message.replies)


@pytest.mark.asyncio
async def test_profile_timezone_save_back(monkeypatch: pytest.MonkeyPatch) -> None:
    cancel_mock = AsyncMock(return_value=handlers.END)
    monkeypatch.setattr(handlers, "profile_cancel", cancel_mock)
    run_db_mock = AsyncMock()
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    message = DummyMessage("Назад")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.END
    cancel_mock.assert_awaited_once()
    assert run_db_mock.await_count == 0


@pytest.mark.asyncio
async def test_profile_timezone_save_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(handlers, "build_timezone_webapp_button", lambda: None)
    run_db_mock = AsyncMock()
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    message = DummyMessage("Bad/Zone")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.PROFILE_TZ
    assert any("Некорректный часовой пояс" in r for r in message.replies)
    assert run_db_mock.await_count == 0


@pytest.mark.asyncio
async def test_profile_timezone_save_db_error(monkeypatch: pytest.MonkeyPatch) -> None:
    run_db_mock = AsyncMock(return_value=(True, False))
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    message = DummyMessage("Europe/Moscow")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.END
    assert any("Не удалось обновить" in r for r in message.replies)
    run_db_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_timezone_save_profile_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_db_mock = AsyncMock(return_value=(False, True))
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    message = DummyMessage("Europe/Moscow")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.END
    assert message.replies == ["✅ Профиль создан. Часовой пояс сохранён."]
    run_db_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_timezone_save_success(monkeypatch: pytest.MonkeyPatch) -> None:
    reminder_user = SimpleNamespace(id=1)
    reminder = SimpleNamespace(id=5, user=reminder_user)

    async def run_db_mock(fn, *, sessionmaker):  # type: ignore[override]
        run_db_mock.calls += 1
        return (True, True) if run_db_mock.calls == 1 else [reminder]

    run_db_mock.calls = 0
    monkeypatch.setattr(handlers, "run_db", run_db_mock)

    calls: list[tuple[Any, Any, Any]] = []

    def reschedule(job_queue: Any, rem: Any, user: Any) -> None:
        calls.append((job_queue, rem, user))

    monkeypatch.setattr(handlers.reminder_handlers, "_reschedule_job", reschedule)

    job_queue = object()
    message = DummyMessage("Europe/Moscow")
    update = cast(
        Update,
        SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1)),
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(job_queue=job_queue),
    )
    state = await handlers.profile_timezone_save(update, context)
    assert state == handlers.END
    assert any("Часовой пояс обновлён" in r for r in message.replies)
    assert calls == [(job_queue, reminder, reminder_user)]
    assert run_db_mock.calls == 2


@pytest.mark.parametrize(
    "text, expected_state, expected_fragment",
    [
        ("назад", handlers.PROFILE_ICR, "Введите коэффициент ИКХ"),
        ("abc", handlers.PROFILE_CF, "Введите КЧ числом."),
        ("2,5", handlers.PROFILE_TARGET, "Введите целевой уровень сахара"),
    ],
)
@pytest.mark.asyncio
async def test_profile_cf_cases(
    text: str, expected_state: int, expected_fragment: str
) -> None:
    msg = DummyMessage(text)
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    state = await handlers.profile_cf(update, ctx)
    assert state == expected_state
    assert expected_fragment in msg.replies[0]
    if state == handlers.PROFILE_TARGET:
        assert ctx.user_data is not None
        assert ctx.user_data["profile_cf"] == 2.5


@pytest.mark.parametrize(
    "text, expected_state, expected_fragment",
    [
        ("назад", handlers.PROFILE_CF, "Введите коэффициент чувствительности"),
        ("abc", handlers.PROFILE_TARGET, "Введите целевой сахар числом."),
        ("6", handlers.PROFILE_LOW, "Введите нижний порог сахара"),
    ],
)
@pytest.mark.asyncio
async def test_profile_target_cases(
    text: str, expected_state: int, expected_fragment: str
) -> None:
    msg = DummyMessage(text)
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )
    state = await handlers.profile_target(update, ctx)
    assert state == expected_state
    assert expected_fragment in msg.replies[0]
    if state == handlers.PROFILE_LOW:
        assert ctx.user_data is not None
        assert ctx.user_data["profile_target"] == 6.0


@pytest.mark.parametrize(
    "text, expected_state, expected_fragment",
    [
        ("назад", handlers.PROFILE_TARGET, "Введите целевой уровень сахара"),
        ("abc", handlers.PROFILE_LOW, "Введите нижний порог числом."),
        ("4", handlers.PROFILE_HIGH, "Введите верхний порог сахара"),
    ],
)
@pytest.mark.asyncio
async def test_profile_low_cases(
    text: str, expected_state: int, expected_fragment: str
) -> None:
    msg = DummyMessage(text)
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"profile_target": 6.0}),
    )
    state = await handlers.profile_low(update, ctx)
    assert state == expected_state
    assert expected_fragment in msg.replies[0]
    if state == handlers.PROFILE_HIGH:
        assert ctx.user_data is not None
        assert ctx.user_data["profile_low"] == 4.0


@pytest.mark.parametrize(
    "text, user_data, expected_state, expected_fragment",
    [
        (
            "назад",
            {
                "profile_icr": 8.0,
                "profile_cf": 3.0,
                "profile_target": 6.0,
                "profile_low": 4.0,
            },
            handlers.PROFILE_LOW,
            "Введите нижний порог сахара",
        ),
        (
            "abc",
            {
                "profile_icr": 8.0,
                "profile_cf": 3.0,
                "profile_target": 6.0,
                "profile_low": 4.0,
            },
            handlers.PROFILE_HIGH,
            "Введите верхний порог числом.",
        ),
        (
            "3",
            {
                "profile_icr": 8.0,
                "profile_cf": 3.0,
                "profile_target": 6.0,
                "profile_low": 4.0,
            },
            handlers.PROFILE_HIGH,
            handlers.MSG_HIGH_GT_LOW,
        ),
        (
            "9",
            {
                "profile_icr": 8.0,
                "profile_cf": 3.0,
                "profile_target": 10.0,
                "profile_low": 4.0,
            },
            handlers.PROFILE_HIGH,
            handlers.MSG_TARGET_RANGE,
        ),
    ],
)
@pytest.mark.asyncio
async def test_profile_high_invalid(
    text: str, user_data: dict[str, float], expected_state: int, expected_fragment: str
) -> None:
    msg = DummyMessage(text)
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data=user_data),
    )
    state = await handlers.profile_high(update, ctx)
    assert state == expected_state
    assert expected_fragment in msg.replies[0]


@pytest.mark.asyncio
async def test_profile_high_db_error(monkeypatch: pytest.MonkeyPatch) -> None:
    msg = DummyMessage("9")
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={
                "profile_icr": 8.0,
                "profile_cf": 3.0,
                "profile_target": 6.0,
                "profile_low": 4.0,
            }
        ),
    )
    run_db_mock = AsyncMock(return_value=False)
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    state = await handlers.profile_high(update, ctx)
    assert state == handlers.END
    assert msg.replies[0] == "⚠️ Не удалось сохранить профиль."
    run_db_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_high_success_warning(monkeypatch: pytest.MonkeyPatch) -> None:
    msg = DummyMessage("9")
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    ctx = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={
                "profile_icr": 9.0,
                "profile_cf": 2.0,
                "profile_target": 6.0,
                "profile_low": 4.0,
            }
        ),
    )
    run_db_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(handlers, "run_db", run_db_mock)
    state = await handlers.profile_high(update, ctx)
    assert state == handlers.END
    assert any("Профиль обновлён" in r for r in msg.replies)
    assert any("Проверьте" in r for r in msg.replies)
    run_db_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_profile_edit_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    edit_mock = AsyncMock(return_value=handlers.PROFILE_ICR)
    monkeypatch.setattr(handlers, "profile_edit", edit_mock)
    update = SimpleNamespace()
    context = SimpleNamespace()
    result = await handlers._profile_edit_entry(update, context)
    assert result == handlers.PROFILE_ICR
    edit_mock.assert_awaited_once_with(update, context)
