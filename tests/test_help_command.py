import pytest
from types import SimpleNamespace

import diabetes.common_handlers as handlers


class DummyMessage:
    def __init__(self):
        self.replies = []
        self.kwargs = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_help_command_includes_new_features_and_quick_input():
    message = DummyMessage()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    await handlers.help_command(update, context)

    assert message.kwargs[0]["reply_markup"] == handlers.menu_keyboard
    text = message.replies[0]
    assert "🆕 Новые возможности:\n" in text
    assert "• ✨ Мастер настройки при первом запуске\n" in text
    assert "• 🕹 Быстрый ввод (smart-input)\n" in text
    assert "• ✏️ Редактирование записей\n\n" in text
    menu_part = text.split("📲 Кнопки меню:\n", 1)[1]
    assert "🕹 Быстрый ввод\n" in menu_part
