import services.api.app.diabetes.utils.ui as ui
import services.api.app.ui.keyboard as kb


def test_main_keyboard_preserves_buttons() -> None:
    menu_layout = [[btn.text for btn in row] for row in ui.menu_keyboard().keyboard]
    keyboard_layout = [
        [btn.text for btn in row] for row in kb.build_main_keyboard().keyboard
    ]
    assert keyboard_layout == menu_layout + [
        [kb.LEARN_BUTTON_TEXT],
        [kb.ASSISTANT_AI_BUTTON_TEXT],
    ]


def test_confirm_keyboard_steps_inline_buttons() -> None:
    markup = ui.confirm_keyboard("back")
    texts = [[btn.text for btn in row] for row in markup.inline_keyboard]
    assert texts == [
        ["✅ Подтвердить", "✏️ Исправить"],
        ["❌ Отмена"],
        ["🔙 Назад"],
    ]
