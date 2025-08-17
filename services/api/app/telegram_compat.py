"""Temporary Telegram compatibility helpers.

This module patches :class:`telegram.ext._application.Application` to work on
Python 3.13. The current version of ``python-telegram-bot`` lacks the
``"__weakref__"`` slot which becomes mandatory in Python 3.13 for classes using
``__slots__``. Importing this module adds the missing slot so that
``ApplicationBuilder().build()`` succeeds.

Remove this module once ``python-telegram-bot`` is upgraded and includes the
fix natively.
"""

from telegram.ext._application import Application

if "__weakref__" not in getattr(Application, "__slots__", ()):
    Application.__slots__ = (*Application.__slots__, "__weakref__")  # type: ignore[attr-defined]
