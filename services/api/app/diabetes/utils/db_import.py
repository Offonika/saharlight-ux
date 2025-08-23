from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import cast

logger = logging.getLogger(__name__)

RunDB = Callable[..., Awaitable[object]]


def get_run_db() -> RunDB | None:
    """Safely import ``run_db`` from the services layer.

    Returns
    -------
    ``RunDB`` | ``None``
        ``run_db`` callable when the import succeeds, otherwise ``None``.
    """
    try:
        from services.api.app.diabetes.services.db import run_db as _run_db
    except Exception as exc:  # pragma: no cover - log unexpected errors
        logger.exception("Unexpected error importing run_db", exc_info=exc)
        return None
    return cast(RunDB, _run_db)
