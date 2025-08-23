from __future__ import annotations

from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class SessionProtocol(Protocol):
    """Minimal protocol for DB sessions used by services."""

    def get(self, entity: type[T], ident: Any) -> T | None:
        """Retrieve an entity by primary key."""
        ...

    def delete(self, instance: Any) -> None:
        """Mark an object for deletion."""
        ...
