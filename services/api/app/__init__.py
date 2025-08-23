"""App package initialization."""

# Import compatibility patches for python-telegram-bot before any
# ApplicationBuilder instances are created.  The module modifies the
# ``Application`` class in-place so simply importing it is sufficient.
#
# This makes the patch run automatically whenever ``services.api.app`` or any
# of its subpackages are imported, removing the need for manual imports in
# tests or application code.
from . import telegram_compat  # noqa: F401

__all__: list[str] = []
