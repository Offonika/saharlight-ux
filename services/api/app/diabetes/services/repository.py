from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def commit(session: Session) -> bool:
    """Commit an SQLAlchemy session.

    Parameters
    ----------
    session: Session
        Active SQLAlchemy session.

    Returns
    -------
    bool
        ``True`` if the commit succeeded. If an error occurs the session is
        rolled back, the error is logged and ``False`` is returned.
    """
    try:
        session.commit()
        return True
    except SQLAlchemyError:  # pragma: no cover - logging only
        session.rollback()
        logger.exception("DB commit failed")
        return False


@contextmanager
def transactional(session: Session) -> Iterator[Session]:
    """Context manager that commits on success and rolls back on failure."""
    try:
        yield session
        session.commit()
    except SQLAlchemyError:  # pragma: no cover - logging only
        session.rollback()
        logger.exception("DB commit failed")
        raise
