from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import cast

logger = logging.getLogger(__name__)


def get_run_db() -> Callable[..., Awaitable[object]] | None:
    """Safely import and return ``run_db``.

    Returns ``None`` if the import is not available or fails with an
    unexpected exception.
    """
    try:
        from services.api.app.diabetes.services.db import run_db as _run_db
    except ImportError:  # pragma: no cover - optional db runner
        return None
    except Exception:  # pragma: no cover - log unexpected errors
        logger.exception("Unexpected error importing run_db")
        return None
    return cast(Callable[..., Awaitable[object]], _run_db)
