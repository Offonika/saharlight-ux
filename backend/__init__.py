"""Compatibility layer for legacy backend imports.

This package re-exports modules from ``services.api.app`` to preserve
backward compatibility with older import paths.
"""

from services.api.app import *  # noqa: F401,F403
from services.api.app import (
    bot,
    config,
    diabetes,
    main,
    middleware,
    schemas,
    services,
)

__all__ = [
    "bot",
    "config",
    "diabetes",
    "main",
    "middleware",
    "schemas",
    "services",
]
