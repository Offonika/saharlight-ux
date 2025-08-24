import importlib
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import InlineKeyboardButton, MenuButtonDefault, Update
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    ExtBot,
)


def _reload_config() -> None:
    import services.api.app.config as config

    importlib.reload(config)


@pytest.mark.asyncio
async def test_post_init_sets_default_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://example.com"
    monkeypatch.setenv("WEBAPP_URL", base_url)
    _reload_config()
    import services.api.app.menu_button as menu_button

    importlib.reload(menu_button)

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def fake_set_chat_menu_button(
        self, *args: object, **kwargs: object
    ) -> bool:
        menu_button = kwargs["menu_button"]
        if isinstance(menu_button, list):
            raise BadRequest("Too many menu buttons")
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(ExtBot, "set_chat_menu_button", fake_set_chat_menu_button)

    app = ApplicationBuilder().token("TEST").post_init(menu_button.post_init).build()
    await app.post_init(app)

    assert len(calls) == 1
    _, kwargs = calls[0]
    button = kwargs["menu_button"]
    assert isinstance(button, MenuButtonDefault)


@pytest.mark.asyncio
async def test_open_command_launches_webapp(monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://example.com"
    monkeypatch.setenv("WEBAPP_URL", base_url)
    _reload_config()
    from services.api.app.diabetes.handlers.common_handlers import open_command

    class DummyMessage:
        def __init__(self) -> None:
            self.replies: list[str] = []
            self.kwargs: list[dict[str, Any]] = []

        async def reply_text(self, text: str, **kwargs: Any) -> None:
            self.replies.append(text)
            self.kwargs.append(kwargs)

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await open_command(update, context)

    assert message.kwargs
    markup = message.kwargs[0]["reply_markup"]
    button = markup.inline_keyboard[0][0]
    assert isinstance(button, InlineKeyboardButton)
    assert button.web_app is not None
    assert button.web_app.url == base_url
