import importlib
from types import SimpleNamespace
from typing import Any, Callable, cast

import pytest
from telegram import InlineKeyboardMarkup, WebAppInfo, Update

handlers = importlib.import_module(
    "services.api.app.diabetes.handlers.webapp_openers"
)


class DummyMessage:
    def __init__(self) -> None:
        self.kwargs: list[dict[str, Any]] = []
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("func", "path"),
    [
        (handlers.open_history_webapp, "/history"),
        (handlers.open_profile_webapp, "/profile"),
        (handlers.open_subscription_webapp, "/subscription"),
        (handlers.open_reminders_webapp, "/reminders"),
    ],
)
async def test_webapp_openers(monkeypatch: pytest.MonkeyPatch, func: Callable[..., Any], path: str) -> None:
    base_url = "https://example.com/app/"
    monkeypatch.setattr(handlers.config.settings, "webapp_url", base_url)
    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context: Any = SimpleNamespace()

    await func(update, context)

    assert message.kwargs, "Expected a reply"
    markup = message.kwargs[0].get("reply_markup")
    assert isinstance(markup, InlineKeyboardMarkup)
    button = markup.inline_keyboard[0][0]
    assert isinstance(button.web_app, WebAppInfo)
    assert button.web_app.url == base_url.rstrip("/") + path
