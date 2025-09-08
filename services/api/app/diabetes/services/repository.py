from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class CommitError(RuntimeError):
    """Raised when a database commit fails."""


def commit(session: Session) -> None:
    """Commit an SQLAlchemy session.

    Parameters
    ----------
    session: Session
        Active SQLAlchemy session.

    Raises
    ------
    CommitError
        If the commit fails. On success nothing is returned.
    """
    try:
        session.commit()
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
    except SQLAlchemyError as exc:  # pragma: no cover - logging only
        session.rollback()
        logger.exception("DB transaction failed: %s", exc.__class__.__name__)
        raise
    except Exception:  # pragma: no cover - logging only
        session.rollback()
        logger.exception("Unexpected DB transaction error")
        raise
