from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import Iterator, TypeVar
from warnings import WarningMessage

T = TypeVar("T", bound=Warning)

@contextmanager
def warn_or_not(category: type[T] | None) -> Iterator[list[WarningMessage]]:
    """Assert that a warning of ``category`` is emitted or not.

    When ``category`` is ``None`` the context ensures that no warnings were
    produced.
    """
    with warnings.catch_warnings(record=True) as records:
        warnings.simplefilter("always")
        yield records
        if category is None:
            assert not records, records
        else:
            assert any(issubclass(r.category, category) for r in records), records
