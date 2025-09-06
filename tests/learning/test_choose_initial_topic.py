import pytest

from services.api.app.diabetes.learning_topics import choose_initial_topic


def test_novice_insulin_returns_xe_basics() -> None:
    profile = {"therapy_type": "insulin", "learning_level": "novice"}
    assert choose_initial_topic(profile) == "xe_basics"


@pytest.mark.parametrize("therapy", ["tablets", "none"])
def test_novice_non_insulin_returns_healthy_eating(therapy: str) -> None:
    profile = {"therapy_type": therapy, "learning_level": "novice"}
    assert choose_initial_topic(profile) == "healthy-eating"


@pytest.mark.parametrize("level", ["intermediate", "advanced"])
def test_non_novice_returns_basics_of_diabetes(level: str) -> None:
    profile = {"therapy_type": "insulin", "learning_level": level}
    assert choose_initial_topic(profile) == "basics-of-diabetes"
