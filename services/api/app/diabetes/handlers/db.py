"""Typed wrappers for database helpers used by handlers."""

from __future__ import annotations

from typing import Callable, TypeVar, ParamSpec, Concatenate

from sqlalchemy.orm import Session, sessionmaker

from services.api.app.diabetes.services.db import (
    SessionLocal as _SessionLocal,
    run_db as _run_db,
)

# Explicitly type the session factory so calls to ``SessionLocal()`` are typed.
SessionLocal: sessionmaker[Session] = _SessionLocal

P = ParamSpec("P")
R = TypeVar("R")


async def run_db(
    fn: Callable[Concatenate[Session, P], R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Proxy to :func:`services.api.app.diabetes.services.db.run_db` with types."""

    session_factory: sessionmaker[Session] = kwargs.pop("sessionmaker", SessionLocal)
    return await _run_db(fn, *args, sessionmaker=session_factory, **kwargs)


__all__ = ["SessionLocal", "run_db"]

