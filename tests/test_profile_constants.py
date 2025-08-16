from telegram.ext import ConversationHandler
from services.api.app.diabetes.handlers import profile as profile_handlers


def test_profile_state_constants() -> None:
    states = [
        profile_handlers.PROFILE_ICR,
        profile_handlers.PROFILE_CF,
        profile_handlers.PROFILE_TARGET,
        profile_handlers.PROFILE_LOW,
        profile_handlers.PROFILE_HIGH,
        profile_handlers.PROFILE_TZ,
    ]
    # ensure state constants are unique and sequential starting from 0
    assert states == list(range(6))
    # ensure END constant matches ConversationHandler.END
    assert profile_handlers.END == ConversationHandler.END
    # ensure constants are exported via __all__
    exported = {
        "PROFILE_ICR",
        "PROFILE_CF",
        "PROFILE_TARGET",
        "PROFILE_LOW",
        "PROFILE_HIGH",
        "PROFILE_TZ",
        "END",
    }
    assert exported <= set(profile_handlers.__all__)
