from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.photo_handlers as photo_handlers
import services.api.app.diabetes.utils.functions as functions


# ensure OpenAI env vars for tests
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("OPENAI_ASSISTANT_ID", "asst_test")


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


class DummyMessage:
    def __init__(self, photo: tuple[Any, ...]) -> None:
        self.photo = photo
        self.texts: list[str] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.texts.append(text)


@pytest.mark.asyncio
async def test_photo_handler_ignores_previous_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_as_bytearray(self) -> bytearray:
                return bytearray(b"img")

        return File()

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "new"

    async def fake_send_message(**kwargs: Any) -> Run:
        return Run()

    captured_run_ids: list[str | None] = []

    def list_messages(thread_id: str, run_id: str | None = None) -> Any:
        captured_run_ids.append(run_id)
        return SimpleNamespace(
            data=[
                SimpleNamespace(
                    run_id="old",
                    role="assistant",
                    content=[
                        SimpleNamespace(text=SimpleNamespace(value="old info"))
                    ],
                ),
                SimpleNamespace(
                    run_id="new",
                    role="assistant",
                    content=[
                        SimpleNamespace(text=SimpleNamespace(value="new info"))
                    ],
                ),
            ]
        )

    dummy_client = SimpleNamespace(
        beta=SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(retrieve=lambda thread_id, run_id: Run()),
                messages=SimpleNamespace(list=list_messages),
            )
        )
    )

    extracted: list[str] = []

    def fake_extract(text: str) -> functions.NutritionInfo:
        extracted.append(text)
        return functions.NutritionInfo(carbs_g=30.0, xe=2.0)

    user_data: dict[str, Any] = {"thread_id": "tid"}
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(bot=SimpleNamespace(get_file=fake_get_file), user_data=user_data),
    )
    update = cast(
        Update,
        SimpleNamespace(
            message=DummyMessage(photo=(DummyPhoto(),)),
            effective_user=SimpleNamespace(id=1),
        ),
    )

    monkeypatch.setattr(photo_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(photo_handlers, "_get_client", lambda: dummy_client)
    monkeypatch.setattr(photo_handlers, "extract_nutrition_info", fake_extract)
    monkeypatch.setattr(photo_handlers, "build_main_keyboard", lambda: None)

    await photo_handlers.photo_handler(update, context)

    assert captured_run_ids == ["new"]
    assert extracted == ["new info"]
    entry = user_data["pending_entry"]
    assert entry["carbs_g"] == 30.0
    assert entry["xe"] == 2.0
    assert photo_handlers.WAITING_GPT_FLAG not in user_data
