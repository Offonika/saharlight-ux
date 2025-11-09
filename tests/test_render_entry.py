import datetime
from types import SimpleNamespace
from typing import Any, cast

from services.api.app.diabetes.handlers.reporting_handlers import (
    EntryLike,
    render_entry,
)


def make_entry(**kwargs: Any) -> EntryLike:
    defaults: dict[str, Any] = {
        "event_time": datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        "sugar_before": 5.5,
        "carbs_g": None,
        "xe": None,
        "insulin_short": None,
        "insulin_long": None,
        "dose": 1.0,
        "weight_g": None,
        "protein_g": None,
        "fat_g": None,
        "calories_kcal": None,
    }
    defaults.update(kwargs)
    return cast(EntryLike, SimpleNamespace(**defaults))


def test_render_entry_with_xe_and_carbs() -> None:
    entry: EntryLike = make_entry(carbs_g=50, xe=4.1)
    text = render_entry(entry)
    assert "🍞 Углеводы: <b>50 г (4.1 ХЕ)</b>" in text
    assert "💉 Короткий: <b>1.0 (legacy)</b>" in text
    assert "🕒 Длинный: <b>—</b>" in text


def test_render_entry_with_xe_only() -> None:
    entry: EntryLike = make_entry(carbs_g=None, xe=3.0)
    text = render_entry(entry)
    assert "🍞 Углеводы: <b>3.0 ХЕ</b>" in text


def test_render_entry_without_xe() -> None:
    entry: EntryLike = make_entry(carbs_g=30, xe=None)
    text = render_entry(entry)
    assert "🍞 Углеводы: <b>30 г</b>" in text
    assert "ХЕ" not in text


def test_render_entry_escapes_html() -> None:
    entry: EntryLike = make_entry(dose="<script>")
    text = render_entry(entry)
    assert "💉 Короткий: <b>&lt;script&gt;</b>" in text
    assert "🕒 Длинный: <b>—</b>" in text


def test_render_entry_with_macros() -> None:
    entry: EntryLike = make_entry(weight_g=100, protein_g=5, fat_g=3, calories_kcal=120)
    text = render_entry(entry)
    assert "⚖️ Вес: <b>100 г</b>" in text
    assert "🥩 Белки: <b>5 г</b>" in text
    assert "🧈 Жиры: <b>3 г</b>" in text
    assert "🔥 Калории: <b>120 ккал</b>" in text


def test_render_entry_with_explicit_insulin_values() -> None:
    entry: EntryLike = make_entry(insulin_short=4.5, insulin_long=12.0, dose=None)
    text = render_entry(entry)
    assert "💉 Короткий: <b>4.5</b>" in text
    assert "🕒 Длинный: <b>12.0</b>" in text
