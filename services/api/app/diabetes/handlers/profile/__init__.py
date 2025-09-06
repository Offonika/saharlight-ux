"""Expose profile conversation handlers and helpers."""

from . import api as _api, conversation as _conversation
from .api import fetch_profile, post_profile, save_profile, set_timezone
from .conversation import (
    END,
    PROFILE_CF,
    PROFILE_HIGH,
    PROFILE_ICR,
    PROFILE_LOW,
    PROFILE_TARGET,
    PROFILE_TZ,
    profile_back,
    profile_cancel,
    profile_command,
    profile_conv,
    profile_edit,
    profile_icr,
    profile_security,
    profile_timezone,
    profile_view,
    profile_webapp_handler,
    profile_webapp_save,
)
from .validation import parse_profile_args, parse_profile_values
from services.api.app.diabetes.utils.ui import back_keyboard


def get_api() -> tuple[object, type[Exception], type]:
    return _api.get_api(_conversation.SessionLocal)


__all__ = [
    "profile_command",
    "profile_view",
    "profile_cancel",
    "profile_back",
    "profile_security",
    "profile_timezone",
    "profile_edit",
    "profile_conv",
    "profile_icr",
    "profile_webapp_save",
    "profile_webapp_handler",
    "back_keyboard",
    "PROFILE_ICR",
    "PROFILE_CF",
    "PROFILE_TARGET",
    "PROFILE_LOW",
    "PROFILE_HIGH",
    "PROFILE_TZ",
    "END",
    "get_api",
    "save_profile",
    "set_timezone",
    "fetch_profile",
    "post_profile",
    "parse_profile_args",
    "parse_profile_values",
]

# Attach helper functions to the conversation module so tests and other modules
# can monkeypatch or access them directly.
for _attr in (
    "get_api",
    "save_profile",
    "set_timezone",
    "fetch_profile",
    "post_profile",
    "parse_profile_args",
    "parse_profile_values",
    "back_keyboard",
):
    setattr(_conversation, _attr, globals()[_attr])

# Ensure constants are visible when importing this package
_conversation.__all__ = __all__

# Re-export the conversation module as the package itself for backward compatibility.
import sys as _sys  # noqa: E402

_sys.modules[__name__] = _conversation
