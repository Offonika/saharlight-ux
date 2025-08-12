from __future__ import annotations

import logging
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def commit_session(session) -> bool:
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
