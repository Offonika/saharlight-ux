import warnings
from contextlib import contextmanager

import pytest
from types import SimpleNamespace
from typing import Any, Iterator, cast
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import MagicMock
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import CallbackContext

from services.api.app.diabetes.utils.ui import menu_keyboard

from services.api.app.diabetes.services.db import Base, User, Profile, dispose_engine


@contextmanager
def no_warnings() -> Iterator[None]:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        yield


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.markups: list[Any] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)

    async def delete(self) -> None:
        pass


@pytest.mark.parametrize(
    "args, expected_icr, expected_cf, expected_target, expected_low, expected_high",
    [
        (["8", "3", "6", "4", "9"], "8.0", "3.0", "6.0", "4.0", "9.0"),
        (["8,5", "3,1", "6,7", "3,2", "8,2"], "8.5", "3.1", "6.7", "3.2", "8.2"),
        (
            ["icr=8", "cf=3", "target=6", "low=4", "high=9"],
            "8.0",
            "3.0",
            "6.0",
            "4.0",
            "9.0",
        ),
        (
            ["target=6", "icr=8", "cf=3", "low=4", "high=9"],
            "8.0",
            "3.0",
            "6.0",
            "4.0",
            "9.0",
        ),
        (["i=8", "c=3", "t=6", "l=4", "h=9"], "8.0", "3.0", "6.0", "4.0", "9.0"),
    ],
)
@pytest.mark.asyncio
async def test_profile_command_and_view(
    monkeypatch: pytest.MonkeyPatch,
    args: Any,
    expected_icr: Any,
    expected_cf: Any,
    expected_target: Any,
    expected_low: Any,
    expected_high: Any,
) -> None:
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    from services.api.app.diabetes.handlers import profile as handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=123, thread_id="t"))
        session.commit()

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=123))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=args, user_data={}),
    )

    message2 = DummyMessage()
    update2 = cast(
        Update,
        SimpleNamespace(message=message2, effective_user=SimpleNamespace(id=123)),
    )
    context2 = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    with no_warnings():
        await handlers.profile_command(update, context)
        await handlers.profile_view(update2, context2)
        dispose_engine(engine)

    assert message.markups[0] is menu_keyboard
    assert f"• ИКХ: {expected_icr} г/ед." in message.texts[0]
    assert f"• КЧ: {expected_cf} ммоль/л" in message.texts[0]
    assert f"• Целевой сахар: {expected_target} ммоль/л" in message.texts[0]
    assert f"• Низкий порог: {expected_low} ммоль/л" in message.texts[0]
    assert f"• Высокий порог: {expected_high} ммоль/л" in message.texts[0]

    assert f"• ИКХ: {expected_icr} г/ед." in message2.texts[0]
    assert f"• КЧ: {expected_cf} ммоль/л" in message2.texts[0]
    assert f"• Целевой сахар: {expected_target} ммоль/л" in message2.texts[0]
    assert f"• Низкий порог: {expected_low} ммоль/л" in message2.texts[0]
    assert f"• Высокий порог: {expected_high} ммоль/л" in message2.texts[0]
    markup = message2.markups[0]
    assert isinstance(markup, InlineKeyboardMarkup)
    buttons = [b for row in markup.inline_keyboard for b in row]
    callbacks = {b.text: b.callback_data for b in buttons}
    assert callbacks["✏️ Изменить"] == "profile_edit"
    assert callbacks["🔙 Назад"] == "profile_back"


@pytest.mark.parametrize(
    "args, expected_attr",
    [
        (["0", "3", "6", "4", "9"], "MSG_ICR_GT0"),
        (["icr=0", "cf=3", "target=6", "low=4", "high=9"], "MSG_ICR_GT0"),
        (["8", "0", "6", "4", "9"], "MSG_CF_GT0"),
        (["icr=8", "cf=0", "target=6", "low=4", "high=9"], "MSG_CF_GT0"),
        (["8", "3", "0", "4", "9"], "MSG_TARGET_GT0"),
        (["icr=8", "cf=3", "target=0", "low=4", "high=9"], "MSG_TARGET_GT0"),
        (["8", "3", "6", "0", "9"], "MSG_LOW_GT0"),
        (["icr=8", "cf=3", "target=6", "low=0", "high=9"], "MSG_LOW_GT0"),
        (["8", "3", "6", "4", "3"], "MSG_HIGH_GT_LOW"),
        (["icr=8", "cf=3", "target=6", "low=4", "high=3"], "MSG_HIGH_GT_LOW"),
    ],
)
@pytest.mark.asyncio
async def test_profile_command_invalid_values(
    monkeypatch: pytest.MonkeyPatch, args: Any, expected_attr: str
) -> None:
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    from services.api.app.diabetes.handlers import profile as handlers

    commit_mock = MagicMock()
    session_local_mock = MagicMock()
    post_profile_mock = MagicMock()
    monkeypatch.setattr(handlers, "commit", commit_mock)
    monkeypatch.setattr(handlers, "SessionLocal", session_local_mock)
    monkeypatch.setattr(handlers, "post_profile", post_profile_mock)

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=args, user_data={}),
    )

    await handlers.profile_command(update, context)

    assert commit_mock.call_count == 0
    assert session_local_mock.call_count == 0
    assert post_profile_mock.call_count == 0
    expected_msg = getattr(handlers, expected_attr)
    assert any(expected_msg in t for t in message.texts)


@pytest.mark.asyncio
async def test_profile_command_help_and_dialog(monkeypatch: pytest.MonkeyPatch) -> None:
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    from services.api.app.diabetes.handlers import profile as handlers

    # Test /profile help
    help_msg = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=help_msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=["help"], user_data={}),
    )
    result = await handlers.profile_command(update, context)
    assert result == handlers.END
    assert "Формат команды" in help_msg.texts[0]

    # Test starting dialog with empty args
    dialog_msg = DummyMessage()
    update2 = cast(
        Update,
        SimpleNamespace(message=dialog_msg, effective_user=SimpleNamespace(id=1)),
    )
    context2 = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=[], user_data={}),
    )
    result2 = await handlers.profile_command(update2, context2)
    assert result2 == handlers.PROFILE_ICR
    assert dialog_msg.texts[0].startswith("Введите коэффициент ИКХ")
    assert dialog_msg.markups[0] is handlers.back_keyboard


@pytest.mark.asyncio
async def test_profile_view_preserves_user_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import os

    os.environ["OPENAI_API_KEY"] = "test"
    os.environ["OPENAI_ASSISTANT_ID"] = "asst_test"
    import services.api.app.diabetes.utils.openai_utils as openai_utils  # noqa: F401
    from services.api.app.diabetes.handlers import profile as handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    monkeypatch.setattr(handlers, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=1, thread_id="tid"))
        session.add(Profile(telegram_id=1, icr=10, cf=2, target_bg=6))
        session.commit()

    message = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={"thread_id": "tid", "foo": "bar"}),
    )

    with no_warnings():
        await handlers.profile_view(update, context)
        dispose_engine(engine)

    assert context.user_data is not None
    user_data = context.user_data
    assert user_data["thread_id"] == "tid"
    assert user_data["foo"] == "bar"


@pytest.mark.asyncio
async def test_profile_view_missing_profile_shows_webapp_button(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from urllib.parse import urlparse
    from services.api.app.config import settings as config_settings
    from services.api.app.diabetes.handlers import profile as handlers

    monkeypatch.setattr(config_settings, "webapp_url", "https://example.com")
    monkeypatch.setattr(handlers, "settings", config_settings, raising=False)
    monkeypatch.setattr(handlers, "get_api", lambda: (object(), Exception, None))
    monkeypatch.setattr(handlers, "fetch_profile", lambda api, exc, user_id: None)

    msg = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.profile_view(update, context)

    assert msg.texts[0].startswith("Ваш профиль пока не настроен.")
    markup = msg.markups[0]
    button = markup.inline_keyboard[0][0]
    assert button.text == "📝 Заполнить форму"
    assert button.web_app is not None
    assert urlparse(button.web_app.url).path == "/ui/profile"
