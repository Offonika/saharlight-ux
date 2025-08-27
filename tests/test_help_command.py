from typing import Any

import pytest
import services.api.app.diabetes.handlers.common_handlers as handlers
from tests.helpers import make_context, make_update


class DummyMessage:
    def __init__(self) -> None:
        self.replies: list[str] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(self, text: str, **kwargs: Any) -> None:
        self.replies.append(text)
        self.kwargs.append(kwargs)


@pytest.mark.asyncio
async def test_help_includes_new_features() -> None:
    """Ensure /help mentions wizard, smart-input and edit features."""

    message = DummyMessage()
    update = make_update(message=message)
    context = make_context()

    await handlers.help_command(update, context)

    assert message.kwargs[0]["reply_markup"] == handlers.build_menu_keyboard()
    text = message.replies[0]
    assert "🆕 Новые возможности:\n" in text
    assert "• ✨ Мастер настройки при первом запуске\n" in text
    assert "• 🕹 Быстрый ввод (smart-input)\n" in text
    assert "• ✏️ Редактирование записей\n\n" in text


@pytest.mark.asyncio
async def test_help_includes_security_block() -> None:
    """Ensure /help mentions security settings."""

    message = DummyMessage()
    update = make_update(message=message)
    context = make_context()

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "🔔 Безопасность:\n" in text
    assert "Пороги" in text
    assert "SOS-уведомления" in text
    assert "Напоминания" in text
    assert "/hypoalert" in text
    assert "/profile" in text


@pytest.mark.asyncio
async def test_help_lists_reminder_commands_and_menu_button() -> None:
    """Ensure reminder commands and menu button are documented."""

    message = DummyMessage()
    update = make_update(message=message)
    context = make_context()

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "/reminders - список напоминаний\n" in text
    assert "/addreminder - добавить напоминание\n" in text
    assert "/delreminder - удалить напоминание\n" in text
    assert "⏰ Напоминания\n" in text


@pytest.mark.asyncio
async def test_help_lists_sos_contact_command() -> None:
    """Ensure /help documents SOS contact configuration."""

    message = DummyMessage()
    update = make_update(message=message)
    context = make_context()

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "/soscontact — настроить контакт для SOS-уведомлений\n" in text
