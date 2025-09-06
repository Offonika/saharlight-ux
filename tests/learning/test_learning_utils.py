from __future__ import annotations

import pytest

from services.api.app.diabetes.learning_utils import choose_initial_topic


@pytest.mark.parametrize(
    "profile, expected",
    [
        (
            {"learning_level": "novice", "therapy_type": "insulin"},
            ("insulin-usage", "Инсулин"),
        ),
        (
            {"learning_level": "novice", "therapy_type": "tablets"},
            ("basics-of-diabetes", "Основы диабета"),
        ),
        (
            {"learning_level": "novice", "therapy_type": "none"},
            ("basics-of-diabetes", "Основы диабета"),
        ),
        (
            {"learning_level": "expert", "therapy_type": "insulin"},
            ("xe_basics", "Хлебные единицы"),
        ),
        (
            {"learning_level": "expert", "therapy_type": "none"},
            ("healthy-eating", "Здоровое питание"),
        ),
    ],
)

def test_choose_initial_topic(profile: dict[str, str], expected: tuple[str, str]) -> None:
    assert choose_initial_topic(profile) == expected
