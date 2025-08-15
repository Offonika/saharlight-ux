import logging
from typing import Any, TYPE_CHECKING

from sqlalchemy.orm import Session

from services.api.app.config import settings
from services.api.app.diabetes.services.db import Profile, User
from services.api.app.diabetes.services.repository import commit

logger = logging.getLogger(__name__)


if TYPE_CHECKING:
    from diabetes_sdk.api.default_api import DefaultApi


def get_api() -> tuple[Any, Any, Any]:
    """Return API client, its exception type and profile model.

    Separate function to make API access testable without importing SDK in UI
    modules.
    """
    try:
        from diabetes_sdk.api.default_api import DefaultApi
        from diabetes_sdk.api_client import ApiClient
        from diabetes_sdk.configuration import Configuration
        from diabetes_sdk.exceptions import ApiException
        from diabetes_sdk.models.profile import Profile as ProfileModel
    except ImportError:
        logger.warning(
            "diabetes_sdk is required but not installed. Install it with 'pip install -r requirements.txt'."
        )
        return None, None, None
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
) -> Any:
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
