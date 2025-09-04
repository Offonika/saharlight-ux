from datetime import UTC, datetime, timedelta
from services.api.app.diabetes.onboarding_state import OnboardingStateStore
from tests.utils.warn_ctx import warn_or_not


def test_continue_after_restart() -> None:
    store = OnboardingStateStore()
    store.set_step(1, 2)
    data = store.to_dict()
    with warn_or_not(None):
        restored = OnboardingStateStore.from_dict(data)
    assert restored.get(1).step == 2


def test_auto_reset_after_inactivity() -> None:
    store = OnboardingStateStore()
    state = store.get(1)
    state.step = 2
    state.updated_at = datetime.now(UTC) - timedelta(days=15)
    with warn_or_not(None):
        new_state = store.get(1)
    assert new_state.step == 0
