from services.api.app.services.onboarding_state import OnboardingState
from .services.db import Base

metadata = Base.metadata

__all__ = ["metadata", "OnboardingState"]
