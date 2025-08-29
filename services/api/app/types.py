from __future__ import annotations

from typing import Any, Mapping, Protocol, Sequence, TypeVar

T = TypeVar("T")


class SessionProtocol(Protocol):
    """Minimal protocol for DB sessions used by services."""

    def get(self, entity: type[T], ident: object) -> T | None:
        """Retrieve an entity by primary key."""
        ...

    def delete(self, instance: object) -> None:
        """Mark an object for deletion."""
        ...

    def execute(
        self,
        statement: Any,
        params: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None = None,
    ) -> Any:
        """Execute a SQL statement."""
        ...
