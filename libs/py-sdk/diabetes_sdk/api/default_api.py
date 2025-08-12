from ..api_client import ApiClient


class DefaultApi:
    """Placeholder default API client."""

    def __init__(self, api_client: ApiClient | None = None, *, configuration=None) -> None:
        if api_client is not None:
            self.api_client = api_client
        else:
            self.api_client = ApiClient(configuration)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"DefaultApi(api_client={self.api_client!r})"
