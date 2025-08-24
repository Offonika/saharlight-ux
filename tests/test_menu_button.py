import importlib

import pytest
from telegram import MenuButtonDefault, MenuButtonWebApp
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
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(ExtBot, "set_chat_menu_button", fake_set_chat_menu_button)

    app = ApplicationBuilder().token("TEST").post_init(menu_button.post_init).build()
    await app.post_init(app)

    assert len(calls) == 1
    _, kwargs = calls[0]

    buttons = kwargs["menu_button"]
    assert isinstance(buttons, list)
    assert len(buttons) == 4
    paths = ["/reminders", "/history", "/profile", "/subscription"]
    for btn, path in zip(buttons, paths):
        assert isinstance(btn, MenuButtonWebApp)
        assert btn.web_app is not None
        assert urlparse(btn.web_app.url).path == path


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
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(ExtBot, "set_chat_menu_button", fake_set_chat_menu_button)

    app = ApplicationBuilder().token("TEST").post_init(menu_button.post_init).build()
    await app.post_init(app)

    assert len(calls) == 1
    _, kwargs = calls[0]
    button = kwargs["menu_button"]
    assert isinstance(button, MenuButtonDefault)

