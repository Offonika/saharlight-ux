import pytest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers


class DummyMessage:
    def __init__(self, text: str | None = None, photo: list[Any] | None = None) -> None:
        self.text: str | None = text
        self.photo: list[Any] | None = photo
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


@pytest.mark.asyncio
async def test_photo_prompt_includes_dish_name(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                return bytearray(b"img")

        return File()

    async def fake_send_chat_action(*args: Any, **kwargs: Any) -> None:
        pass

    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(
            user_data={"thread_id": "tid"},
            bot=SimpleNamespace(
                get_file=fake_get_file, send_chat_action=fake_send_chat_action
            ),
        ),
    )

    captured = {}

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "runid"

    async def fake_send_message(**kwargs: Any) -> Run:
        captured["content"] = kwargs["content"]
        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(retrieve=lambda thread_id, run_id: Run()),
                messages=SimpleNamespace(
                    list=lambda thread_id: SimpleNamespace(
                        data=[
                            SimpleNamespace(
                                role="assistant",
                                content=[
                                    SimpleNamespace(
                                        text=SimpleNamespace(
                                            value="Борщ\nУглеводы: 30 г\nХЕ: 2"
                                        )
                                    )
                                ],
                            )
                        ]
                    )
                ),
            )
        )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(photo_handlers, "build_main_keyboard", lambda: None)

    msg_photo = DummyMessage(photo=[DummyPhoto()])
    update = cast(
        Update,
        SimpleNamespace(message=msg_photo, effective_user=SimpleNamespace(id=1)),
    )

    await photo_handlers.photo_handler(update, context)

    assert "название" in captured["content"]
    # Final reply should include dish name from Vision response
    assert any("Борщ" in reply for reply in msg_photo.replies)
    assert context.user_data is not None
    user_data = context.user_data
    entry = user_data.get("pending_entry")
    assert entry is not None
    assert entry["carbs_g"] == 30
    assert entry["xe"] == 2
