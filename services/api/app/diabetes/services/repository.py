from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CommitError(Exception):
    """Raised when a database commit fails."""


def commit(session: Session) -> bool:
    """Commit an SQLAlchemy session.

    Parameters
    ----------
    session: Session
        Active SQLAlchemy session.

    Returns
    -------
    bool
        ``True`` if the commit succeeded.

    Raises
    ------
    CommitError
        If the commit fails. The session is rolled back and the error is logged.
    """
    try:
        session.commit()
        return True
    except SQLAlchemyError as exc:  # pragma: no cover - logging only
        session.rollback()
        logger.exception("DB commit failed")
        raise CommitError from exc


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
