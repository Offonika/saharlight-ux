"""Expose profile conversation handlers and helpers."""

from . import conversation as _conversation
from .api import get_api, save_profile, set_timezone, fetch_profile, post_profile
from .validation import parse_profile_args

# Attach helper functions to the conversation module so tests and other modules
# can monkeypatch or access them directly.
_conversation.get_api = get_api
_conversation.save_profile = save_profile
_conversation.set_timezone = set_timezone
_conversation.fetch_profile = fetch_profile
_conversation.post_profile = post_profile
_conversation.parse_profile_args = parse_profile_args

# Re-export the conversation module as the package itself
import sys as _sys
_sys.modules[__name__] = _conversation
