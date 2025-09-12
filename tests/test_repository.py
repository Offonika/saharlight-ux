from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from services.api.app.diabetes.services import repository


class DummyError(SQLAlchemyError):
    """Custom SQLAlchemy error for testing."""


def test_commit_success() -> None:
    session = MagicMock()
    repository.commit(session)
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_commit_failure() -> None:
    session = MagicMock()
    session.commit.side_effect = DummyError("boom")
    with pytest.raises(repository.CommitError):
        repository.commit(session)
    session.rollback.assert_called_once()


def test_transactional_success() -> None:
    session = MagicMock()
    with repository.transactional(session) as sess:
        assert sess is session
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_transactional_failure() -> None:
    session = MagicMock()
    with pytest.raises(DummyError):
        with repository.transactional(session):
            raise DummyError("boom")
    session.rollback.assert_called_once()
    session.commit.assert_not_called()


def test_transactional_value_error() -> None:
    session = MagicMock()
    with pytest.raises(ValueError):
        with repository.transactional(session):
            raise ValueError("boom")
    session.rollback.assert_not_called()
    session.commit.assert_not_called()
