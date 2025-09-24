from __future__ import annotations

import importlib

import pytest
from telegram import MenuButtonDefault
from telegram.error import BadRequest
from telegram.ext import ApplicationBuilder, ExtBot


def _reload_config() -> None:
    import services.api.app.config as config

    importlib.reload(config)


@pytest.mark.asyncio
async def test_post_init_configures_default_menu(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("WEBAPP_URL", raising=False)
    _reload_config()
    import services.api.app.menu_button as menu_button

    importlib.reload(menu_button)

    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    async def fake_set_chat_menu_button(self, *args: object, **kwargs: object) -> bool:
        menu_button_obj = kwargs["menu_button"]
        if isinstance(menu_button_obj, list):
            raise BadRequest("Too many menu buttons")
        calls.append((args, kwargs))
        return True

    monkeypatch.setattr(ExtBot, "set_chat_menu_button", fake_set_chat_menu_button)

    app = ApplicationBuilder().token("TEST").post_init(menu_button.post_init).build()

    await app.post_init(app)

    assert len(calls) == 1
    first_button = calls[0][1]["menu_button"]
    assert isinstance(first_button, MenuButtonDefault)

    base_url = "https://web.example/app"
    monkeypatch.setenv("WEBAPP_URL", base_url)

    await app.post_init(app)

    assert len(calls) == 2
    button = calls[-1][1]["menu_button"]
    assert isinstance(button, MenuButtonDefault)
