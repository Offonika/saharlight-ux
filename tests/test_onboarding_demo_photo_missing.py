import logging
import os
from types import SimpleNamespace
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.api.app.diabetes.services.db import Base
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.photos: list[tuple[Any, str | None]] = []
        self.markups: list[Any] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))

    async def reply_photo(
        self, photo: Any, caption: str | None = None, **kwargs: Any
    ) -> None:
        self.photos.append((photo, caption))
        self.markups.append(kwargs.get("reply_markup"))


@pytest.mark.asyncio
async def test_onboarding_demo_photo_missing(monkeypatch: Any, caplog: Any) -> None:
    os.environ.setdefault("OPENAI_API_KEY", "test")
    os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")

    import services.api.app.diabetes.handlers.common_handlers  # noqa: F401
    import services.api.app.diabetes.handlers.onboarding_handlers as onboarding
    import services.api.app.diabetes.services.gpt_client as gpt_client

    monkeypatch.setattr(gpt_client, "create_thread", lambda: "tid")

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(onboarding, "SessionLocal", TestSession)
    monkeypatch.setattr(onboarding, "build_menu_keyboard", lambda: "MK")

    message = DummyMessage()
    update = make_update(
        message=message, effective_user=SimpleNamespace(id=1, first_name="Ann")
    )
    context = make_context(user_data={}, bot_data={})

    await onboarding.start_command(update, context)
    update.message.text = "10"
    await onboarding.onboarding_icr(update, context)
    update.message.text = "3"
    await onboarding.onboarding_cf(update, context)
    update.message.text = "6"
    await onboarding.onboarding_target(update, context)

    import pathlib

    orig_open = pathlib.Path.open

    def fake_open(self, *args: Any, **kwargs: Any) -> None:
        if self == onboarding.DEMO_PHOTO_PATH:
            raise OSError("missing")
        return orig_open(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "open", fake_open)

    update.message.text = "Europe/Moscow"
    with caplog.at_level(logging.ERROR):
        state = await onboarding.onboarding_timezone(update, context)

    assert state == onboarding.ONB_DEMO
    assert not message.photos
    assert "Демо-фото недоступно" in message.texts[-1]
    assert any("Failed to open demo photo" in r.message for r in caplog.records)
