import services.api.app.diabetes.handlers.common_handlers as handlers
import services.api.app.diabetes.utils.ui as ui


def test_menu_keyboard_webapp_layout() -> None:
    keyboard_texts = [[btn.text for btn in row] for row in handlers.menu_keyboard().keyboard]
    assert keyboard_texts == [
        [ui.PHOTO_BUTTON_TEXT, ui.SUGAR_BUTTON_TEXT],
        [ui.DOSE_BUTTON_TEXT, ui.REPORT_BUTTON_TEXT],
        [ui.QUICK_INPUT_BUTTON_TEXT, ui.HELP_BUTTON_TEXT],
        [ui.SOS_BUTTON_TEXT],
    ]
