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
async def test_help_includes_new_features():
    """Ensure /help mentions wizard, smart-input and edit features."""

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


@pytest.mark.asyncio
async def test_help_includes_security_block():
    """Ensure /help mentions security settings."""

    message = DummyMessage()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "🔔 Безопасность:\n" in text
    assert "Пороги" in text
    assert "SOS-уведомления" in text
    assert "Напоминания" in text
    assert "/hypoalert" in text
    assert "/profile" in text


@pytest.mark.asyncio
async def test_help_lists_reminder_commands_and_menu_button():
    """Ensure reminder commands and menu button are documented."""

    message = DummyMessage()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "/reminders - список напоминаний\n" in text
    assert "/addreminder - добавить напоминание\n" in text
    assert "/delreminder - удалить напоминание\n" in text
    assert "⏰ Напоминания\n" in text


@pytest.mark.asyncio
async def test_help_lists_sos_contact_command():
    """Ensure /help documents SOS contact configuration."""

    message = DummyMessage()
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "/soscontact — настроить контакт для SOS-уведомлений\n" in text
