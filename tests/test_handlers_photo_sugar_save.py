from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

import services.api.app.diabetes.handlers.dose_handlers as dose_handlers
import services.api.app.diabetes.handlers.common_handlers as common_handlers


class DummyMessage:
    def __init__(self, text: str | None = None, photo: list[Any] | None = None):
        self.text = text
        self.photo = photo
        self.replies: list[tuple[str, dict[str, Any]]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append((text, kwargs))


class DummyQuery:
    def __init__(self, data: str):
        self.data = data
        self.edited: list[str] = []

    async def answer(self) -> None:
        pass

    async def edit_message_text(self, text: str, **kwargs: Any) -> None:
        self.edited.append(text)


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


class DummySession:
    def __init__(self):
        self.added = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        pass

    def get(self, model, user_id):
        return SimpleNamespace(icr=10.0, cf=1.0, target_bg=6.0)


session = DummySession()


@pytest.mark.asyncio
async def test_photo_flow_saves_entry(monkeypatch, tmp_path) -> None:
    async def fake_parse_command(text: str) -> dict[str, Any]:
        return {"action": "add_entry", "fields": {}, "entry_date": None, "time": None}

    monkeypatch.setattr(dose_handlers, "parse_command", fake_parse_command)
    monkeypatch.setattr(dose_handlers, "confirm_keyboard", lambda: None)
    monkeypatch.setattr(dose_handlers, "menu_keyboard", None)

    msg_start = DummyMessage("/dose")
    update_start = SimpleNamespace(
        message=msg_start, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(user_data={})
    await dose_handlers.freeform_handler(update_start, context)

    monkeypatch.chdir(tmp_path)

    async def fake_get_file(file_id: str) -> Any:
        class File:
            async def download_to_drive(self, path: str) -> None:
                Path(path).write_bytes(b"img")

        return File()

    context.bot = SimpleNamespace(get_file=fake_get_file)

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "runid"

    async def fake_send_message(**kwargs):
        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(
                    retrieve=lambda thread_id, run_id: Run()
                ),
                messages=SimpleNamespace(
                    list=lambda thread_id: SimpleNamespace(
                        data=[
                            SimpleNamespace(
                                role="assistant",
                                content=[
                                    SimpleNamespace(
                                        text=SimpleNamespace(value="carbs 30g xe 2")
                                    )
                                ],
                            )
                        ]
                    )
                ),
            )
        )

    monkeypatch.setattr(dose_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(dose_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(dose_handlers, "extract_nutrition_info", lambda text: (30.0, 2.0))
    context.user_data["thread_id"] = "tid"

    msg_photo = DummyMessage(photo=[DummyPhoto()])
    update_photo = SimpleNamespace(
        message=msg_photo, effective_user=SimpleNamespace(id=1)
    )
    await dose_handlers.photo_handler(update_photo, context)

    entry = context.user_data["pending_entry"]
    assert entry["carbs_g"] == 30.0
    assert entry["xe"] == 2.0
    assert entry["photo_path"].endswith("uid.jpg")

    msg_sugar = DummyMessage("5.5")
    update_sugar = SimpleNamespace(
        message=msg_sugar, effective_user=SimpleNamespace(id=1)
    )
    dose_handlers.SessionLocal = lambda: session
    await dose_handlers.freeform_handler(update_sugar, context)
    assert context.user_data["pending_entry"]["sugar_before"] == 5.5

    monkeypatch.setattr(common_handlers, "SessionLocal", lambda: session)
    import services.api.app.diabetes.handlers.alert_handlers as alert_handlers

    async def noop(*a: Any, **k: Any) -> None:
        return None

    monkeypatch.setattr(alert_handlers, "check_alert", noop)

    query = DummyQuery("confirm_entry")
    update_confirm = SimpleNamespace(callback_query=query)
    await common_handlers.callback_router(update_confirm, context)

    assert len(session.added) == 1
    saved = session.added[0]
    assert saved.carbs_g == 30.0
    assert saved.sugar_before == 5.5
    assert "pending_entry" not in context.user_data
    assert query.edited == ["✅ Запись сохранена в дневник!"]

