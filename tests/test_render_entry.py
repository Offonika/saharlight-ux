import datetime
from types import SimpleNamespace

from services.api.app.diabetes.handlers.reporting_handlers import render_entry


def make_entry(**kwargs):
    defaults = dict(
        event_time=datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
        sugar_before=5.5,
        carbs_g=None,
        xe=None,
        dose=1.0,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_render_entry_with_xe_and_carbs():
    entry = make_entry(carbs_g=50, xe=4.1)
    text = render_entry(entry)
    assert "🍞 Углеводы: <b>50 г (4.1 ХЕ)</b>" in text


def test_render_entry_with_xe_only():
    entry = make_entry(carbs_g=None, xe=3.0)
    text = render_entry(entry)
    assert "🍞 Углеводы: <b>3.0 ХЕ</b>" in text


def test_render_entry_without_xe():
    entry = make_entry(carbs_g=30, xe=None)
    text = render_entry(entry)
    assert "🍞 Углеводы: <b>30 г</b>" in text
    assert "ХЕ" not in text


def test_render_entry_escapes_html():
    entry = make_entry(dose="<script>")
    text = render_entry(entry)
    assert "&lt;script&gt;" in text
