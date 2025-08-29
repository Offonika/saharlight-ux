from services.api.app.diabetes.handlers.profile.conversation import _profile_saved_message


def test_profile_saved_message_basic() -> None:
    assert _profile_saved_message(1.0, 2.0, 3.0, 4.0, 5.0) == (
        "✅ Профиль обновлён:\n"
        "• ИКХ: 1.0 г/ед.\n"
        "• КЧ: 2.0 ммоль/л\n"
        "• Целевой сахар: 3.0 ммоль/л\n"
        "• Низкий порог: 4.0 ммоль/л\n"
        "• Высокий порог: 5.0 ммоль/л"
    )


def test_profile_saved_message_with_warning() -> None:
    warning = "\n⚠️ предупреждение"
    assert _profile_saved_message(1.0, 2.0, 3.0, 4.0, 5.0, warning) == (
        "✅ Профиль обновлён:\n"
        "• ИКХ: 1.0 г/ед.\n"
        "• КЧ: 2.0 ммоль/л\n"
        "• Целевой сахар: 3.0 ммоль/л\n"
        "• Низкий порог: 4.0 ммоль/л\n"
        "• Высокий порог: 5.0 ммоль/л\n"
        "⚠️ предупреждение"
    )

