from services.api.app.diabetes.handlers import dose_calc, photo_handlers, sugar_handlers


def test_photo_sugar_state_uses_sugar_handler() -> None:
    handlers = dose_calc.dose_conv.states.get(photo_handlers.PHOTO_SUGAR)
    assert handlers, "PHOTO_SUGAR state is missing"
    callbacks = {h.callback for h in handlers}
    assert dose_calc.dose_sugar in callbacks or sugar_handlers.sugar_val in callbacks, (
        "PHOTO_SUGAR state not linked to a sugar handler"
    )
