import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from services.api.app.config import settings
from services.api.app.diabetes.services.db import Profile, User
from services.api.app.diabetes.services.repository import commit


logger = logging.getLogger(__name__)


class ProfileSaveError(Exception):
    """Raised when persisting profile data fails."""


@dataclass
class LocalProfile:
    """Minimal profile model used when the external SDK is unavailable."""

    telegram_id: int
    icr: float | None = None
    cf: float | None = None
    target: float | None = None
    low: float | None = None
    high: float | None = None


class LocalProfileAPI:
    """Very small stand-in for :mod:`diabetes_sdk`'s API client.

    It stores profile data directly in the local database using the project's
    SQLAlchemy models.  The implementation is intentionally minimal – only the
    calls used by the bot are provided.
    """

    @staticmethod
    def _sessionmaker():
        # Import here to avoid circular imports and to pick up monkeypatched
        # session factories from tests.
        from services.api.app.diabetes.handlers import profile as handlers

        return handlers.SessionLocal

    def profiles_post(self, profile: LocalProfile) -> None:
        """Persist ``profile`` to the database."""

        SessionLocal = self._sessionmaker()
        with SessionLocal() as session:
            ok = save_profile(
                session,
                profile.telegram_id,
                profile.icr or 0.0,
                profile.cf or 0.0,
                profile.target or 0.0,
                profile.low or 0.0,
                profile.high or 0.0,
            )
            if not ok:
                raise ProfileSaveError("Failed to save profile")

    def profiles_get(self, telegram_id: int) -> LocalProfile | None:
        """Return a profile for ``telegram_id`` from the database."""

        SessionLocal = self._sessionmaker()
        with SessionLocal() as session:
            prof = session.get(Profile, telegram_id)
            if prof is None:
                return None
            return LocalProfile(
                telegram_id=prof.telegram_id,
                icr=prof.icr,
                cf=prof.cf,
                target=prof.target_bg,
                low=prof.low_threshold,
                high=prof.high_threshold,
            )


if TYPE_CHECKING:  # pragma: no cover - used only for type hints
    from diabetes_sdk.api.default_api import DefaultApi


def get_api() -> tuple[object, type[Exception], type]:
    """Return API client, its exception type and profile model.

    The function attempts to import and configure the external
    :mod:`diabetes_sdk`.  If the SDK is unavailable for any reason, a
    lightweight local implementation is returned instead.  This ensures the
    rest of the code can operate without having to handle ``None`` values.
    """
    try:  # pragma: no cover - exercised in tests but flagged for clarity
        from diabetes_sdk.api.default_api import DefaultApi
        from diabetes_sdk.api_client import ApiClient
        from diabetes_sdk.configuration import Configuration
        from diabetes_sdk.exceptions import ApiException
        from diabetes_sdk.models.profile import Profile as ProfileModel
    except ImportError:  # pragma: no cover - import failure is tested separately
        logger.warning(
            "diabetes_sdk is not installed. Falling back to local profile API.",
        )
        return LocalProfileAPI(), Exception, LocalProfile
    except RuntimeError:  # pragma: no cover - initialization issues
        logger.warning(
            "diabetes_sdk could not be initialized. Falling back to local profile API.",
        )
        return LocalProfileAPI(), Exception, LocalProfile
    api = DefaultApi(ApiClient(Configuration(host=settings.api_url)))
    return api, ApiException, ProfileModel


def save_profile(
    session: Session,
    user_id: int,
    icr: float,
    cf: float,
    target: float,
    low: float,
    high: float,
) -> bool:
    """Persist profile values into the local database."""
    prof = session.get(Profile, user_id)
    if not prof:
        prof = Profile(telegram_id=user_id)
        session.add(prof)
    prof.icr = icr
    prof.cf = cf
    prof.target_bg = target
    prof.low_threshold = low
    prof.high_threshold = high
    return bool(commit(session))


def set_timezone(session: Session, user_id: int, tz: str) -> tuple[bool, bool]:
    """Update user timezone in the database."""
    user = session.get(User, user_id)
    if not user:
        return False, False
    user.timezone = tz
    ok = bool(commit(session))
    return True, ok


def fetch_profile(
    api: "DefaultApi",
    ApiException: type[Exception],
    user_id: int,
) -> object | None:
    """Fetch profile via synchronous SDK call."""
    try:
        return api.profiles_get(telegram_id=user_id)
    except ApiException:
        return None


def post_profile(
    api: "DefaultApi",
    ApiException: type[Exception],
    ProfileModel: type,
    user_id: int,
    icr: float,
    cf: float,
    target: float,
    low: float,
    high: float,
) -> tuple[bool, str | None]:
    """Save profile via SDK and return success flag and optional error message."""
    profile = ProfileModel(
        telegram_id=user_id,
        icr=icr,
        cf=cf,
        target=target,
        low=low,
        high=high,
    )
    try:
        api.profiles_post(profile)
        return True, None
    except ApiException as exc:
        logger.error("API call failed: %s", exc)
        return False, str(exc)
