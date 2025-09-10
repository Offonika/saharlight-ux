import logging

from services.api.app.diabetes.handlers.onboarding_handlers import (
    _next_step,
    _prev_step,
    _step_num,
)


def test_step_helpers_invalid_step_logs_warning(caplog) -> None:
    variant = "A"
    with caplog.at_level(logging.WARNING):
        assert _step_num(99, variant) == 1
    assert "variant order" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert _next_step(99, variant) is None
    assert "variant order" in caplog.text
    caplog.clear()
    with caplog.at_level(logging.WARNING):
        assert _prev_step(99, variant) is None
    assert "variant order" in caplog.text
