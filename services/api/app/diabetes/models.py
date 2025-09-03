from services.api.app.services.onboarding_state import OnboardingState  # noqa: F401
from .services.db import Base

metadata = Base.metadata

__all__ = ["metadata"]
