import pytest
from types import SimpleNamespace
from typing import Any, cast

from telegram import Update
from telegram.ext import CallbackContext

import services.api.app.diabetes.handlers.dose_calc as dose_calc


@pytest.mark.asyncio
async def test_reexported_names_available(monkeypatch: pytest.MonkeyPatch) -> None:
    commit_marker = object()
    parse_marker = object()
    smart_marker = object()
    send_report_marker = object()

    async def dummy_freeform_handler(update: Any, context: Any) -> None:
        handlers = dose_calc._gpt_handlers  # type: ignore[attr-defined]
        assert handlers.commit is commit_marker
        assert handlers.parse_command is parse_marker
        assert handlers.smart_input is smart_marker
        assert handlers.send_report is send_report_marker

    monkeypatch.setattr(dose_calc, "commit", commit_marker)
    monkeypatch.setattr(dose_calc, "parse_command", parse_marker)
    monkeypatch.setattr(dose_calc, "smart_input", smart_marker)
    monkeypatch.setattr(dose_calc, "send_report", send_report_marker)
    gpt_handlers = dose_calc._gpt_handlers  # type: ignore[attr-defined]
    monkeypatch.setattr(gpt_handlers, "freeform_handler", dummy_freeform_handler)

    assert "commit" in dose_calc.__all__
    assert "parse_command" in dose_calc.__all__
    assert "smart_input" in dose_calc.__all__
    assert "send_report" in dose_calc.__all__

    await dose_calc.freeform_handler(
        cast(Update, SimpleNamespace()),
        cast(CallbackContext[Any, Any, Any, Any], SimpleNamespace()),
    )
