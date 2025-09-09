import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import time as time_type
from typing import TYPE_CHECKING, cast

from sqlalchemy.orm import Session
from fastapi import HTTPException

from services.api.app import config
from services.api.app.diabetes.schemas.profile import ProfileSettingsIn
from services.api.app.diabetes.services.db import Profile, User, SessionLocal
from services.api.app.diabetes.services.repository import CommitError, commit


logger = logging.getLogger(__name__)

_sdk_warning_emitted = False


def _warn_sdk_once(message: str) -> None:
    """Log ``message`` only once for missing ``diabetes_sdk``."""

    global _sdk_warning_emitted
    if not _sdk_warning_emitted:
        logger.warning(message)
        _sdk_warning_emitted = True


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
    dia: float | None = None
    round_step: float | None = None
    carb_units: str | None = None
    grams_per_xe: float | None = None
    glucose_units: str | None = None
    therapy_type: str | None = None
    rapid_insulin_type: str | None = None
    prebolus_min: int | None = None
    max_bolus: float | None = None
    postmeal_check_min: int | None = None
    quiet_start: time_type | None = None
    quiet_end: time_type | None = None
    timezone: str | None = None


@dataclass
class LocalProfileSettings:
    """Local representation of profile settings when SDK is unavailable."""

    telegram_id: int
    timezone: str = "UTC"
    timezone_auto: bool = True
    dia: float = 4.0
    round_step: float = 0.5
    carb_units: str = "g"
    grams_per_xe: float = 12.0
    glucose_units: str = "mmol/L"


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
            existing: Profile | None = session.get(Profile, profile.telegram_id)

            def _resolve(value: float | None, attr: str) -> float:
                if value is not None:
                    return value
                if existing is not None:
                    existing_value = cast(float | None, getattr(existing, attr))
                    if existing_value is not None:
                        return existing_value
                raise ProfileSaveError(f"Missing value for {attr}")

            icr = _resolve(profile.icr, "icr")
            cf = _resolve(profile.cf, "cf")
            target = _resolve(profile.target, "target_bg")
            low = _resolve(profile.low, "low_threshold")
            high = _resolve(profile.high, "high_threshold")

            ok = save_profile(
                session,
                profile.telegram_id,
                icr,
                cf,
                target,
                low,
                high,
                sos_contact=profile.sos_contact,
                sos_alerts_enabled=profile.sos_alerts_enabled,
                dia=profile.dia,
                round_step=profile.round_step,
                carb_units=profile.carb_units,
                grams_per_xe=profile.grams_per_xe,
                glucose_units=profile.glucose_units,
                therapy_type=profile.therapy_type,
                rapid_insulin_type=profile.rapid_insulin_type,
                prebolus_min=profile.prebolus_min,
                max_bolus=profile.max_bolus,
                postmeal_check_min=profile.postmeal_check_min,
                quiet_start=profile.quiet_start,
                quiet_end=profile.quiet_end,
                timezone=profile.timezone,
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
                dia=prof.dia,
                round_step=prof.round_step,
                carb_units=prof.carb_units,
                grams_per_xe=prof.grams_per_xe,
                glucose_units=prof.glucose_units,
                therapy_type=prof.therapy_type,
                rapid_insulin_type=prof.insulin_type,
                prebolus_min=prof.prebolus_min,
                max_bolus=prof.max_bolus,
                postmeal_check_min=prof.postmeal_check_min,
                quiet_start=prof.quiet_start,
                quiet_end=prof.quiet_end,
                timezone=prof.timezone,
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
    if not settings.api_url:
        return LocalProfileAPI(sessionmaker), Exception, LocalProfile
    try:  # pragma: no cover - exercised in tests but flagged for clarity
        from diabetes_sdk.api.default_api import DefaultApi
        from diabetes_sdk.api_client import ApiClient
        from diabetes_sdk.configuration import Configuration
        from diabetes_sdk.exceptions import ApiException
        from diabetes_sdk.models.profile import Profile as ProfileModel
    except ImportError:  # pragma: no cover - import failure is tested separately
        _warn_sdk_once(
            "diabetes_sdk is not installed. Falling back to local profile API.",
        )
        return LocalProfileAPI(sessionmaker), Exception, LocalProfile
    except RuntimeError:  # pragma: no cover - initialization issues
        _warn_sdk_once(
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
    *,
    sos_contact: str | None = None,
    sos_alerts_enabled: bool = True,
    dia: float | None = None,
    round_step: float | None = None,
    carb_units: str | None = None,
    grams_per_xe: float | None = None,
    glucose_units: str | None = None,
    therapy_type: str | None = None,
    rapid_insulin_type: str | None = None,
    prebolus_min: int | None = None,
    max_bolus: float | None = None,
    postmeal_check_min: int | None = None,
    quiet_start: time_type | None = None,
    quiet_end: time_type | None = None,
    timezone: str | None = None,
) -> bool:
    """Persist profile values into the local database."""
    if user_id <= 0:
        raise HTTPException(status_code=422, detail="telegram id must be positive")

    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    prof = session.get(Profile, user_id)
    if prof is None:
        prof = Profile(telegram_id=user_id)
        session.add(prof)
    prof.icr = icr
    prof.cf = cf
    prof.target_bg = target
    prof.low_threshold = low
    prof.high_threshold = high
    prof.sos_contact = sos_contact
    prof.sos_alerts_enabled = sos_alerts_enabled
    if dia is not None:
        prof.dia = dia
    if round_step is not None:
        prof.round_step = round_step
    if carb_units is not None:
        prof.carb_units = carb_units
    if grams_per_xe is not None:
        prof.grams_per_xe = grams_per_xe
    if glucose_units is not None:
        prof.glucose_units = glucose_units
    if therapy_type is not None:
        prof.therapy_type = therapy_type
    if rapid_insulin_type is not None:
        prof.insulin_type = rapid_insulin_type
    if prebolus_min is not None:
        prof.prebolus_min = prebolus_min
    if max_bolus is not None:
        prof.max_bolus = max_bolus
    if postmeal_check_min is not None:
        prof.postmeal_check_min = postmeal_check_min
    if quiet_start is not None:
        prof.quiet_start = quiet_start
    if quiet_end is not None:
        prof.quiet_end = quiet_end
    if timezone is not None:
        prof.timezone = timezone
    try:
        commit(session)
    except CommitError:
        return False
    return True


def set_timezone(
    session: Session, user_id: int, tz: str, *, auto: bool
) -> tuple[bool, bool]:
    """Update user timezone in the database.

    Returns ``(existed, ok)`` where ``existed`` shows whether the profile was
    present before the update and ``ok`` indicates commit success.
    """
    return patch_user_settings(
        session,
        user_id,
        ProfileSettingsIn(timezone=tz, timezoneAuto=auto),
    )


def get_profile_settings(session: Session, user_id: int) -> LocalProfileSettings | None:
    """Fetch user settings from the database."""
    profile = session.get(Profile, user_id)
    if not profile:
        return None
    return LocalProfileSettings(
        telegram_id=profile.telegram_id,
        timezone=profile.timezone,
        timezone_auto=profile.timezone_auto,
        dia=profile.dia,
        round_step=profile.round_step,
        carb_units=profile.carb_units,
        grams_per_xe=profile.grams_per_xe,
        glucose_units=profile.glucose_units,
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
    if data.gramsPerXe is not None:
        profile.grams_per_xe = data.gramsPerXe
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
    if (
        profile.timezone_auto
        and device_tz
        and data.timezone is None
        and profile.timezone != device_tz
    ):
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
