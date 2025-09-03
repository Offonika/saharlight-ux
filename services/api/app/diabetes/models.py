from services.api.app.models.onboarding_state import OnboardingState
from .services.db import Base

metadata = Base.metadata

__all__ = ["metadata", "OnboardingState"]
