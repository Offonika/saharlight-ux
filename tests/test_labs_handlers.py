from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.api.app.diabetes import labs_handlers


def test_parse_labs_basic() -> None:
    text = "Глюкоза: 5 (3.3-5.5)\nHbA1c: 7 (4-6)\nALT: 41 (10-40)\nМетформин 500 мг"
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
    ctx.user_data = {"waiting_labs": True, "assistant_last_mode": "labs"}

    result = await labs_handlers.labs_handler(update, ctx)

    assert result == labs_handlers.END
    assert ctx.user_data.get("waiting_labs") is None
    assert ctx.user_data.get("assistant_last_mode") is None
    message.reply_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_labs_handler_unsupported_mime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    update = MagicMock()
    message = MagicMock()
    message.text = None
    message.reply_text = AsyncMock()
    update.effective_message = message
    ctx = MagicMock()
    ctx.user_data = {"waiting_labs": True, "assistant_last_mode": "labs"}
    monkeypatch.setattr(
        labs_handlers,
        "_download_file",
        AsyncMock(return_value=(b"data", "application/zip")),
    )
    result = await labs_handlers.labs_handler(update, ctx)
    assert result == labs_handlers.END
    message.reply_text.assert_awaited_once()
    assert ctx.user_data.get("waiting_labs") is None
    assert ctx.user_data.get("assistant_last_mode") is None
    assert labs_handlers.AWAITING_KIND not in ctx.user_data


@pytest.mark.asyncio
async def test_labs_handler_download_error(monkeypatch: pytest.MonkeyPatch) -> None:
    update = MagicMock()
    message = MagicMock()
    message.text = None
    message.reply_text = AsyncMock()
    update.effective_message = message
    ctx = MagicMock()
    ctx.user_data = {"waiting_labs": True, "assistant_last_mode": "labs"}
    monkeypatch.setattr(
        labs_handlers,
        "_download_file",
        AsyncMock(return_value=None),
    )

    result = await labs_handlers.labs_handler(update, ctx)

    assert result == labs_handlers.END
    message.reply_text.assert_awaited_once_with("⚠️ Не удалось получить файл.")
    assert ctx.user_data.get("waiting_labs") is None
    assert ctx.user_data.get("assistant_last_mode") is None
