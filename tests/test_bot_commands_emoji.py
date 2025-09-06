from __future__ import annotations

import services.bot.main as main


def test_commands_include_emojis() -> None:
    """Command descriptions include emojis for better UX."""
    expected = [
        ("start", "🚀 Запустить бота"),
        ("menu", "📋 Главное меню"),
        ("profile", "👤 Мой профиль"),
        ("report", "📊 Отчёт"),
        ("history", "📚 История записей"),
        ("sugar", "🩸 Расчёт сахара"),
        ("gpt", "🤖 Чат с GPT"),
        ("reminders", "⏰ Список напоминаний"),
        ("help", "❓ Справка"),
        ("trial", "🎁 Trial"),
        ("upgrade", "💳 Оформить PRO"),
    ]
    assert [(c.command, c.description) for c in main.commands] == expected
