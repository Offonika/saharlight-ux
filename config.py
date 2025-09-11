"""Application-wide configuration helpers.

This module exposes selected environment variables and provides a
:func:`validate_tokens` helper that can be used to assert the presence of
required variables.  In tests we often import modules that depend on
configuration, but the full set of production environment variables is
not available.  ``validate_tokens`` therefore accepts an optional list of
variable names to check instead of assuming a fixed, exhaustive list.

If called without arguments no validation is performed, keeping imports
lightweight.  When running the real application, callers can pass the
variables that are mandatory for their context.
"""

from __future__ import annotations

import os
from typing import Iterable

from services.api.app.config import reload_settings, settings

# Expose commonly used environment variables so importing modules can
# reference them directly if needed.  Values default to ``None`` when not
# provided which is convenient for tests where most variables are unset.
TELEGRAM_TOKEN = settings.telegram_token
ONBOARDING_VIDEO_URL = settings.onboarding_video_url
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
PENDING_LOG_LIMIT = settings.pending_log_limit


def validate_tokens(required: Iterable[str] | None = None) -> None:
    """Validate that the given environment variables are present.

    Providing a non-empty ``required`` list also refreshes the application
    settings so that subsequent checks see the latest environment values.

    Parameters
    ----------
    required:
        Iterable of environment variable names to validate.  If ``None``
        (the default) no variables are considered mandatory.

    Raises
    ------
    RuntimeError
        If any of the requested variables are missing from the
        environment.
    """

    required_vars = list(required or [])
    missing = []

    if required_vars:
        reload_settings()

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )
