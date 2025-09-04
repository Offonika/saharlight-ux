import pytest
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import MagicMock

from services.api.app.diabetes.handlers import profile as handlers


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.markups: list[Any] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))


@pytest.mark.asyncio
async def test_profile_view_handles_dict_times(monkeypatch: pytest.MonkeyPatch) -> None:
    dummy_profile = SimpleNamespace(
        icr=8,
        cf=3,
        target=6,
        low=4,
        high=9,
        quiet_start={"hour": 8, "minute": 30},
        quiet_end={"hour": 22, "minute": 15},
    )
    dummy_api = SimpleNamespace(profiles_get=lambda telegram_id: dummy_profile)
    monkeypatch.setattr(handlers, "get_api", lambda: (dummy_api, Exception, MagicMock))

    msg = DummyMessage()
    update = cast(
        Any, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=1))
    )
    context = cast(Any, SimpleNamespace())

    await handlers.profile_view(update, context)

    assert any("08:30-22:15" in text for text in msg.texts)
