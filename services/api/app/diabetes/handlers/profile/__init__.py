"""Expose profile conversation handlers and helpers."""

from . import conversation as _conversation
from .api import get_api, save_profile, set_timezone, fetch_profile, post_profile
from .conversation import (
    profile_command,
    profile_view,
    profile_cancel,
    profile_back,
    profile_security,
    profile_timezone,
    profile_edit,
    profile_conv,
    profile_icr,
    profile_webapp_save,
    profile_webapp_handler,
    back_keyboard,
    PROFILE_ICR,
    PROFILE_CF,
    PROFILE_TARGET,
    PROFILE_LOW,
    PROFILE_HIGH,
    PROFILE_TZ,
    END,
)
from .validation import parse_profile_args

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
]

# Attach helper functions to the conversation module so tests and other modules
# can monkeypatch or access them directly.
_conversation.get_api = get_api
_conversation.save_profile = save_profile
_conversation.set_timezone = set_timezone
_conversation.fetch_profile = fetch_profile
_conversation.post_profile = post_profile
_conversation.parse_profile_args = parse_profile_args

# Ensure constants are visible when importing this package
_conversation.__all__ = [
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
]

# Re-export the conversation module as the package itself for backward compatibility.
import sys as _sys

_sys.modules[__name__] = _conversation

