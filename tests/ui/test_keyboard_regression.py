import services.api.app.diabetes.utils.ui as ui
import services.api.app.ui.keyboard as kb


def test_main_keyboard_preserves_buttons() -> None:
    keyboard_layout = [[btn.text for btn in row] for row in kb.build_main_keyboard().keyboard]
    assert keyboard_layout == [
        [ui.PHOTO_BUTTON_TEXT, ui.SUGAR_BUTTON_TEXT],
        [ui.DOSE_BUTTON_TEXT, ui.REPORT_BUTTON_TEXT],
        [ui.QUICK_INPUT_BUTTON_TEXT, ui.HELP_BUTTON_TEXT],
        [ui.SOS_BUTTON_TEXT],
        [kb.ASSISTANT_BUTTON_TEXT],
    ]


def test_confirm_keyboard_steps_inline_buttons() -> None:
    markup = ui.confirm_keyboard("back")
    texts = [[btn.text for btn in row] for row in markup.inline_keyboard]
    assert texts == [
        ["✅ Подтвердить", "✏️ Исправить"],
        ["❌ Отмена"],
        ["🔙 Назад"],
    ]
