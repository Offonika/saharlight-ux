import importlib

import pytest
from telegram import MenuButtonDefault, MenuButtonWebApp
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, ExtBot


def _reload_config() -> None:
    import services.api.app.config as config

    importlib.reload(config)


@pytest.mark.asyncio
async def test_post_init_sets_chat_menu(monkeypatch: pytest.MonkeyPatch) -> None:
    base_url = "https://example.com"
    monkeypatch.setenv("WEBAPP_URL", base_url)
    _reload_config()
    import services.api.app.menu_button as menu_button

    importlib.reload(menu_button)

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def fake_set_chat_menu_button(self, *args: object, **kwargs: object) -> bool:
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
    assert isinstance(button, MenuButtonWebApp)
    assert button.text == "Menu"
    assert button.web_app is not None
    assert button.web_app.url == base_url


@pytest.mark.asyncio
async def test_post_init_uses_default_menu_without_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    _reload_config()
    import services.api.app.menu_button as menu_button

    importlib.reload(menu_button)

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def fake_set_chat_menu_button(self, *args: object, **kwargs: object) -> bool:
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
