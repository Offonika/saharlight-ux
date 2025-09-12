from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api.app.diabetes import labs_handlers


def test_parse_labs_basic() -> None:
    text = (
        "Глюкоза: 5 (3.3-5.5)\n"
        "HbA1c: 7 (4-6)\n"
        "ALT: 41 (10-40)\n"
        "Метформин 500 мг"
    )
    results = labs_handlers.parse_labs(text)
    names = [r.name for r in results]
    assert "Глюкоза" in names
    assert "HbA1c" in names
    assert "ALT" in names
    # Medication line ignored
    assert all("Метформин" not in r.name for r in results)


@pytest.mark.asyncio
async def test_labs_handler_text() -> None:
    update = MagicMock()
    message = MagicMock()
    message.text = "Глюкоза: 5 (3.3-5.5)"
    message.reply_text = AsyncMock()
    update.effective_message = message
    ctx = MagicMock()
    ctx.user_data = {"waiting_labs": True}

    result = await labs_handlers.labs_handler(update, ctx)

    assert result == labs_handlers.END
    assert ctx.user_data.get("waiting_labs") is None
    message.reply_text.assert_awaited_once()
