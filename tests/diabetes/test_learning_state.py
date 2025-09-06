from services.api.app.diabetes.learning_state import (
    LearnState,
    clear_state,
    get_state,
    set_state,
)


def test_state_roundtrip() -> None:
    data: dict[str, object] = {}
    state = LearnState(topic="t", step=1, awaiting_answer=True, last_step_text="a")
    set_state(data, state)
    assert get_state(data) == state
    clear_state(data)
    assert get_state(data) is None
