from __future__ import annotations

from services.api.app.diabetes.learning_utils import choose_initial_topic


def test_choose_initial_topic_novice_insulin() -> None:
    profile = {"learning_level": "novice", "therapyType": "insulin"}
    assert choose_initial_topic(profile) == ("insulin-usage", "Инсулин")


def test_choose_initial_topic_novice_non_insulin() -> None:
    profile = {"learning_level": "novice", "therapyType": "tablets"}
    assert choose_initial_topic(profile) == ("basics-of-diabetes", "Основы диабета")


def test_choose_initial_topic_non_novice_insulin() -> None:
    profile = {"learning_level": "expert", "therapyType": "insulin"}
    assert choose_initial_topic(profile) == ("xe_basics", "Хлебные единицы")


def test_choose_initial_topic_non_novice_non_insulin() -> None:
    profile = {"learning_level": "expert", "therapyType": "none"}
    assert choose_initial_topic(profile) == ("healthy-eating", "Здоровое питание")
