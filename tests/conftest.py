from collections.abc import Iterator
import warnings

import pytest

from services.api.app.diabetes.services.db import dispose_engine


warnings.filterwarnings(
    "ignore", category=ResourceWarning, module=r"anyio\.streams\.memory"
)


@pytest.fixture(autouse=True, scope="session")
def _dispose_engine_after_tests() -> Iterator[None]:
    """Dispose the global database engine after the test session."""
    yield
    dispose_engine()
