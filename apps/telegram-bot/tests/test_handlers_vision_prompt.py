import pytest
from pathlib import Path
from types import SimpleNamespace

import diabetes.dose_handlers as dose_handlers


class DummyMessage:
    def __init__(self, text=None, photo=None):
        self.text = text
        self.photo = photo
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append((text, kwargs))


class DummyPhoto:
    file_id = "fid"
    file_unique_id = "uid"


@pytest.mark.asyncio
async def test_photo_prompt_includes_dish_name(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    async def fake_get_file(file_id):
        class File:
            async def download_to_drive(self, path):
                Path(path).write_bytes(b"img")

        return File()

    async def fake_send_chat_action(*args, **kwargs):
        pass

    context = SimpleNamespace(
        user_data={"thread_id": "tid"},
        bot=SimpleNamespace(get_file=fake_get_file, send_chat_action=fake_send_chat_action),
    )

    captured = {}

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "runid"

    def fake_send_message(**kwargs):
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

    monkeypatch.setattr(dose_handlers, "send_message", fake_send_message)
    monkeypatch.setattr(dose_handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(dose_handlers, "menu_keyboard", None)

    msg_photo = DummyMessage(photo=[DummyPhoto()])
    update = SimpleNamespace(message=msg_photo, effective_user=SimpleNamespace(id=1))

    await dose_handlers.photo_handler(update, context)

    assert "название" in captured["content"]
    # Final reply should include dish name from Vision response
    assert any("Борщ" in reply[0] for reply in msg_photo.replies)
    entry = context.user_data.get("pending_entry")
    assert entry["carbs_g"] == 30
    assert entry["xe"] == 2
