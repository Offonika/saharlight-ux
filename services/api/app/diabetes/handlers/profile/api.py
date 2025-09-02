import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from services.api.app import config
from services.api.app.diabetes.schemas.profile import ProfileSettingsIn
from services.api.app.diabetes.services.db import Profile, User, SessionLocal
from services.api.app.diabetes.services.repository import CommitError, commit


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
    sos_contact: str | None = None
    sos_alerts_enabled: bool = True


@dataclass
class LocalUserSettings:
    """Local representation of profile settings when SDK is unavailable."""

    telegram_id: int
    timezone: str = "UTC"
    timezone_auto: bool = True
    dia: float = 4.0
    round_step: float = 0.5
    carb_units: str = "g"


class LocalProfileAPI:
    """Very small stand-in for :mod:`diabetes_sdk`'s API client.

    It stores profile data directly in the local database using the project's
    SQLAlchemy models.  The implementation is intentionally minimal – only the
    calls used by the bot are provided.
    """

    def __init__(self, sessionmaker: Callable[[], Session] = SessionLocal) -> None:
        self._sessionmaker = sessionmaker

    def profiles_post(self, profile: LocalProfile) -> None:
        """Persist ``profile`` to the database."""

        with self._sessionmaker() as session:
            ok = save_profile(
                session,
                profile.telegram_id,
                profile.icr or 0.0,
                profile.cf or 0.0,
                profile.target or 0.0,
                profile.low or 0.0,
                profile.high or 0.0,
                profile.sos_contact,
                profile.sos_alerts_enabled,
            )
            if not ok:
                raise ProfileSaveError("Failed to save profile")

    def profiles_get(self, telegram_id: int) -> LocalProfile | None:
        """Return a profile for ``telegram_id`` from the database."""

        with self._sessionmaker() as session:
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
                sos_contact=prof.sos_contact,
                sos_alerts_enabled=prof.sos_alerts_enabled,
            )


if TYPE_CHECKING:  # pragma: no cover - used only for type hints
    from diabetes_sdk.api.default_api import DefaultApi


def get_api(
    sessionmaker: Callable[[], Session] = SessionLocal,
    settings: config.Settings | None = None,
) -> tuple[object, type[Exception], type]:
    """Return API client, its exception type and profile model.

    The function attempts to import and configure the external
    :mod:`diabetes_sdk`.  If the SDK is unavailable for any reason, a
    lightweight local implementation is returned instead.  This ensures the
    rest of the code can operate without having to handle ``None`` values.
    """
    settings = settings or config.get_settings()
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
        return LocalProfileAPI(sessionmaker), Exception, LocalProfile
    except RuntimeError:  # pragma: no cover - initialization issues
        logger.warning(
            "diabetes_sdk could not be initialized. Falling back to local profile API.",
        )
        return LocalProfileAPI(sessionmaker), Exception, LocalProfile
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
    sos_contact: str | None = None,
    sos_alerts_enabled: bool = True,
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
    prof.sos_contact = sos_contact
    prof.sos_alerts_enabled = sos_alerts_enabled
    try:
        commit(session)
    except CommitError:
        return False
    return True


def set_timezone(session: Session, user_id: int, tz: str) -> tuple[bool, bool]:
    """Update user timezone in the database.

    Returns ``(existed, ok)`` where ``existed`` shows whether the profile was
    present before the update and ``ok`` indicates commit success.
    """
    return patch_user_settings(session, user_id, ProfileSettingsIn(timezone=tz))


def get_user_settings(session: Session, user_id: int) -> LocalUserSettings | None:
    """Fetch user settings from the database."""
    profile = session.get(Profile, user_id)
    if not profile:
        return None
    return LocalUserSettings(
        telegram_id=profile.telegram_id,
        timezone=profile.timezone,
        timezone_auto=profile.timezone_auto,
        dia=profile.dia,
        round_step=profile.round_step,
        carb_units=profile.carb_units,
    )


def patch_user_settings(
    session: Session,
    user_id: int,
    data: ProfileSettingsIn,
    device_tz: str | None = None,
) -> tuple[bool, bool]:
    """Persist user settings updating only provided values.

    Returns ``(existed, ok)`` where ``existed`` reflects whether the profile
    existed prior to this call and ``ok`` indicates if the commit succeeded.
    """
    user = session.get(User, user_id)
    if not user:
        user = User(telegram_id=user_id, thread_id="api")
        session.add(user)
    profile = session.get(Profile, user_id)
    existed = profile is not None
    if profile is None:
        profile = Profile(telegram_id=user_id)
        session.add(profile)
    if data.timezone is not None:
        profile.timezone = data.timezone
    if data.timezoneAuto is not None:
        profile.timezone_auto = data.timezoneAuto
    if data.dia is not None:
        profile.dia = data.dia
    if data.roundStep is not None:
        profile.round_step = data.roundStep
    if data.carbUnits is not None:
        profile.carb_units = data.carbUnits.value
    if data.sosContact is not None:
        profile.sos_contact = data.sosContact
    if data.sosAlertsEnabled is not None:
        profile.sos_alerts_enabled = data.sosAlertsEnabled
    if data.therapyType is not None:
        profile.therapy_type = data.therapyType.value
    if data.rapidInsulinType is not None:
        profile.insulin_type = data.rapidInsulinType.value
    if data.maxBolus is not None:
        profile.max_bolus = data.maxBolus
    if data.preBolus is not None:
        profile.prebolus_min = data.preBolus
    if data.afterMealMinutes is not None:
        profile.postmeal_check_min = data.afterMealMinutes
    if profile.timezone_auto and device_tz and profile.timezone != device_tz:
        profile.timezone = device_tz
    try:
        commit(session)
    except CommitError:
        return existed, False
    return existed, True


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
