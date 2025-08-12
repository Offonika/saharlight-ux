from .configuration import Configuration


class ApiClient:
    """Trivial API client placeholder."""

    def __init__(self, configuration: Configuration | None = None) -> None:
        self.configuration = configuration or Configuration()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"ApiClient(configuration={self.configuration!r})"
