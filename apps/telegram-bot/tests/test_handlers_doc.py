import pytest
from pathlib import Path
from types import SimpleNamespace

import diabetes.dose_handlers as handlers


class DummyMessage:
    def __init__(self, text=None, photo=None):
        self.text = text
        self.photo = photo
        self.texts = []

    async def reply_text(self, text, **kwargs):
        self.texts.append(text)


@pytest.mark.asyncio
async def test_doc_handler_calls_photo_handler(monkeypatch):
    called = SimpleNamespace(flag=False)

    async def fake_photo_handler(update, context):
        called.flag = True
        return "OK"

    class DummyFile:
        async def download_to_drive(self, path):
            self.path = path

    async def fake_get_file(file_id):
        return DummyFile()

    dummy_bot = SimpleNamespace(get_file=fake_get_file)

    document = SimpleNamespace(
        file_name="img.png",
        file_unique_id="uid",
        file_id="fid",
        mime_type="image/png",
    )
    message = SimpleNamespace(document=document, photo=None)
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(bot=dummy_bot, user_data={})

    monkeypatch.setattr(handlers, "photo_handler", fake_photo_handler)
    monkeypatch.setattr(handlers.os, "makedirs", lambda *args, **kwargs: None)

    result = await handlers.doc_handler(update, context)

    assert result == "OK"
    assert called.flag
    assert context.user_data["__file_path"] == "photos/1_uid.png"
    assert update.message.photo == []


@pytest.mark.asyncio
async def test_doc_handler_skips_non_images(monkeypatch):
    called = SimpleNamespace(flag=False)

    async def fake_photo_handler(update, context):
        called.flag = True

    document = SimpleNamespace(
        file_name="file.bin",
        file_unique_id="uid",
        file_id="fid",
        mime_type=None,
    )
    message = SimpleNamespace(document=document, photo=None)
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    monkeypatch.setattr(handlers, "photo_handler", fake_photo_handler)

    result = await handlers.doc_handler(update, context)

    assert result == handlers.ConversationHandler.END
    assert not called.flag
    assert "__file_path" not in context.user_data


@pytest.mark.asyncio
async def test_photo_handler_handles_typeerror():
    message = DummyMessage(photo=None)
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    result = await handlers.photo_handler(update, context)

    assert message.texts == ["❗ Файл не распознан как изображение."]
    assert result == handlers.ConversationHandler.END
    assert handlers.WAITING_GPT_FLAG not in context.user_data


@pytest.mark.asyncio
async def test_photo_handler_preserves_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)

    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    async def reply_text(*args, **kwargs):
        pass

    message = SimpleNamespace(photo=[DummyPhoto()], reply_text=reply_text)
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))

    class DummyFile:
        async def download_to_drive(self, path):
            Path(path).write_bytes(b"img")

    async def fake_get_file(file_id):
        return DummyFile()

    dummy_bot = SimpleNamespace(get_file=fake_get_file)
    context = SimpleNamespace(bot=dummy_bot, user_data={"thread_id": "tid"})

    call = {}

    def fake_send_message(**kwargs):
        call.update(kwargs)

        class Run:
            status = "completed"
            thread_id = kwargs["thread_id"]
            id = "runid"

        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(
                    retrieve=lambda thread_id, run_id: SimpleNamespace(
                        status="completed", thread_id=thread_id, id=run_id
                    )
                ),
                messages=SimpleNamespace(list=lambda thread_id: SimpleNamespace(data=[])),
            )
        )

    monkeypatch.setattr(handlers, "send_message", fake_send_message)
    monkeypatch.setattr(handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(handlers, "extract_nutrition_info", lambda text: (10.0, 1.0))
    monkeypatch.setattr(handlers, "menu_keyboard", None)
    monkeypatch.setattr(
        handlers.os,
        "makedirs",
        lambda path, **kwargs: Path(path).mkdir(parents=True, exist_ok=True),
    )

    result = await handlers.photo_handler(update, context)

    assert call["keep_image"] is True
    assert Path(call["image_path"]).exists()
    assert result == handlers.PHOTO_SUGAR


@pytest.mark.asyncio
async def test_photo_then_freeform_calculates_dose(monkeypatch, tmp_path):
    """photo_handler + freeform_handler produce dose in reply and context."""

    class DummyPhoto:
        file_id = "fid"
        file_unique_id = "uid"

    class DummyFile:
        async def download_to_drive(self, path):
            Path(path).write_bytes(b"img")

    async def fake_get_file(file_id):
        return DummyFile()

    monkeypatch.chdir(tmp_path)
    dummy_bot = SimpleNamespace(get_file=fake_get_file)

    class Run:
        status = "completed"
        thread_id = "tid"
        id = "runid"

    def fake_send_message(**kwargs):
        return Run()

    class DummyClient:
        beta = SimpleNamespace(
            threads=SimpleNamespace(
                runs=SimpleNamespace(retrieve=lambda thread_id, run_id: Run()),
                messages=SimpleNamespace(list=lambda thread_id: SimpleNamespace(data=[])),
            )
        )

    monkeypatch.setattr(handlers, "send_message", fake_send_message)
    monkeypatch.setattr(handlers, "_get_client", lambda: DummyClient())
    monkeypatch.setattr(handlers, "extract_nutrition_info", lambda text: (10.0, 1.0))
    monkeypatch.setattr(handlers, "menu_keyboard", None)
    monkeypatch.setattr(handlers, "confirm_keyboard", lambda: None)

    photo_msg = DummyMessage(photo=[DummyPhoto()])
    update_photo = SimpleNamespace(
        message=photo_msg, effective_user=SimpleNamespace(id=1)
    )
    context = SimpleNamespace(bot=dummy_bot, user_data={"thread_id": "tid"})

    await handlers.photo_handler(update_photo, context)

    class DummySession:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            pass

        def get(self, model, user_id):
            return SimpleNamespace(icr=10.0, cf=1.0, target_bg=6.0)

    handlers.SessionLocal = lambda: DummySession()

    sugar_msg = DummyMessage(text="5")
    update_sugar = SimpleNamespace(
        message=sugar_msg, effective_user=SimpleNamespace(id=1)
    )

    await handlers.freeform_handler(update_sugar, context)

    reply = sugar_msg.texts[0]
    assert "Углеводы: 10.0 г" in reply
    assert "Сахар: 5.0 ммоль/л" in reply
    assert "Ваша доза: 1.0 Ед" in reply
    assert "dose" in context.user_data["pending_entry"]
