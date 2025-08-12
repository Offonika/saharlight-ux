from ..api_client import ApiClient
from ..exceptions import ApiException
from ..models import Profile


class DefaultApi:
    """Very small in-memory API client used in tests."""

    _profiles_store: dict[int, Profile] = {}

    def __init__(self, api_client: ApiClient | None = None, *, configuration=None) -> None:
        if api_client is not None:
            self.api_client = api_client
        else:
            self.api_client = ApiClient(configuration)
        self._profiles = self._profiles_store

    def profiles_post(self, profile: Profile) -> None:
        """Store profile in memory with basic validation."""
        if (
            profile.icr <= 0
            or profile.cf <= 0
            or profile.target <= 0
            or profile.low <= 0
            or profile.high <= 0
            or profile.low >= profile.high
            or not (profile.low < profile.target < profile.high)
        ):
            raise ApiException("Все значения должны быть больше 0")
        self._profiles[profile.telegram_id] = profile

    def profiles_get(self, *, telegram_id: int) -> Profile | None:
        """Retrieve profile by Telegram ID."""
        return self._profiles.get(telegram_id)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"DefaultApi(api_client={self.api_client!r})"
