from __future__ import annotations

import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pypdf.errors import PdfReadError
from telegram.error import TelegramError

from services.api.app.diabetes import labs_handlers


def test_extract_text_from_file_logs_pdf_error(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fake_pdf_reader(_: object) -> None:
        raise PdfReadError("boom")

    monkeypatch.setattr(labs_handlers, "PdfReader", fake_pdf_reader)

    with caplog.at_level(logging.WARNING):
        result = labs_handlers._extract_text_from_file(b"example", "application/pdf")

    assert result == "example"
    assert "Failed to read PDF" in caplog.text


@pytest.mark.asyncio
async def test_download_document_logs_and_returns_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    message = SimpleNamespace(
        document=SimpleNamespace(file_id="file-id", mime_type="application/pdf"),
        photo=None,
    )
    bot = SimpleNamespace(get_file=AsyncMock(side_effect=TelegramError("boom")))
    ctx = SimpleNamespace(bot=bot)

    with caplog.at_level(logging.ERROR):
        result = await labs_handlers._download_file(message, ctx)

    assert result is None
    assert "Failed to download document" in caplog.text


@pytest.mark.asyncio
async def test_download_photo_logs_and_returns_none(caplog: pytest.LogCaptureFixture) -> None:
    message = SimpleNamespace(
        document=None,
        photo=[SimpleNamespace(file_id="small"), SimpleNamespace(file_id="big")],
    )
    download_mock = AsyncMock(side_effect=OSError("io"))
    bot = SimpleNamespace(
        get_file=AsyncMock(
            return_value=SimpleNamespace(download_as_bytearray=download_mock)
        )
    )
    ctx = SimpleNamespace(bot=bot)

    with caplog.at_level(logging.ERROR):
        result = await labs_handlers._download_file(message, ctx)

    assert result is None
    assert "Failed to download photo" in caplog.text
