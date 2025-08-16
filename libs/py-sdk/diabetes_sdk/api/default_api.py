from ..api_client import ApiClient
from ..configuration import Configuration
from ..exceptions import ApiException
from ..models import Profile


class DefaultApi:
    """Very small in-memory API client used in tests."""

    _profiles_store: dict[int, Profile] = {}

    def __init__(self, api_client: ApiClient | None = None, *, configuration: Configuration | None = None) -> None:
        if api_client is not None:
            self.api_client = api_client
        else:
            self.api_client = ApiClient(configuration)
        self._profiles = self._profiles_store

    def profiles_post(self, profile: Profile) -> None:
        """Store profile in memory with basic validation."""
        if profile.telegram_id <= 0:
            raise ApiException("telegram_id must be greater than 0")
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
        if telegram_id <= 0:
            raise ApiException("telegram_id must be greater than 0")
        try:
            return self._profiles[telegram_id]
        except KeyError as exc:
            raise ApiException("profile not found") from exc

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"DefaultApi(api_client={self.api_client!r})"
