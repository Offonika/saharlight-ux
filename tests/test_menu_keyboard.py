import services.api.app.diabetes.utils.ui as ui
import services.api.app.ui.keyboard as kb


def test_menu_keyboard_layout() -> None:
    keyboard_texts = [[btn.text for btn in row] for row in kb.build_main_keyboard().keyboard]
    assert keyboard_texts == [
        [ui.PHOTO_BUTTON_TEXT, ui.SUGAR_BUTTON_TEXT],
        [ui.DOSE_BUTTON_TEXT, ui.REPORT_BUTTON_TEXT],
        [ui.QUICK_INPUT_BUTTON_TEXT, ui.HELP_BUTTON_TEXT],
        [ui.SOS_BUTTON_TEXT],
        [kb.ASSISTANT_BUTTON_TEXT],
    ]
