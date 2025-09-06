from types import SimpleNamespace
from typing import Any, cast

import pytest
from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.common_handlers as handlers


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
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.help_command(update, context)

    assert (
        message.kwargs[0]["reply_markup"].keyboard
        == handlers.menu_keyboard().keyboard
    )
    text = message.replies[0]
    assert "🆕 Новые возможности:\n" in text
    assert "• ✨ Мастер настройки при первом запуске\n" in text
    assert "• 🕹 Быстрый ввод (smart-input)\n" in text
    assert "• ✏️ Редактирование записей\n\n" in text


@pytest.mark.asyncio
async def test_help_includes_security_block() -> None:
    """Ensure /help mentions security settings."""

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

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
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "/reminders - список напоминаний\n" in text
    assert "/addreminder" not in text
    assert "/delreminder" not in text


@pytest.mark.asyncio
async def test_help_lists_sos_contact_command() -> None:
    """Ensure /help documents SOS contact configuration."""

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "/soscontact — настроить контакт для SOS-уведомлений\n" in text


@pytest.mark.asyncio
async def test_help_lists_topics_command() -> None:
    """Ensure /help documents the topics command."""

    message = DummyMessage()
    update = cast(Update, SimpleNamespace(message=message))
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(),
    )

    await handlers.help_command(update, context)

    text = message.replies[0]
    assert "/topics - темы обучения\n" in text
