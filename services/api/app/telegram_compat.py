"""Temporary Telegram compatibility helpers.

This module patches :class:`telegram.ext._application.Application` to work on
Python 3.13. The current version of ``python-telegram-bot`` lacks the
``"__weakref__"`` slot which becomes mandatory in Python 3.13 for classes using
``__slots__``. Importing this module adds the missing slot so that
``ApplicationBuilder().build()`` succeeds.

Remove this module once ``python-telegram-bot`` is upgraded and includes the
fix natively.
"""

from dataclasses import dataclass

import telegram.ext as ext
from telegram.ext import _application, _applicationbuilder

Base = _application.Application

if not hasattr(Base, "__weakref__"):  # pragma: no branch

    @dataclass(slots=True, weakref_slot=True)
    class _CompatApplication(Base):
        pass

    _CompatApplication.__slots__ = (*Base.__slots__, *_CompatApplication.__slots__)

    _application.Application = _CompatApplication
    _applicationbuilder.Application = _CompatApplication
    ext.Application = _CompatApplication
