import pytest
from types import SimpleNamespace

import diabetes.dose_handlers as handlers


class DummyMessage:
    def __init__(self, photo=None):
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
async def test_photo_handler_handles_typeerror():
    message = DummyMessage(photo=None)
    update = SimpleNamespace(message=message, effective_user=SimpleNamespace(id=1))
    context = SimpleNamespace(user_data={})

    result = await handlers.photo_handler(update, context)

    assert message.texts == ["❗ Файл не распознан как изображение."]
    assert result == handlers.ConversationHandler.END
    assert handlers.WAITING_GPT_FLAG not in context.user_data
