from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest

from services.bot.telegram_payments import TelegramPaymentsAdapter


@pytest.mark.asyncio
async def test_create_invoice(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = TelegramPaymentsAdapter(provider_token="token")
    bot = AsyncMock()
    context = SimpleNamespace(bot=bot)
    chat = SimpleNamespace(id=1)
    update = SimpleNamespace(effective_chat=chat)

    await adapter.create_invoice(update, context)

    bot.send_invoice.assert_called_once()


@pytest.mark.asyncio
async def test_handle_pre_checkout_query() -> None:
    adapter = TelegramPaymentsAdapter()
    pre_checkout = AsyncMock()
    update = SimpleNamespace(pre_checkout_query=pre_checkout)
    context = SimpleNamespace()

    await adapter.handle_pre_checkout_query(update, context)

    pre_checkout.answer.assert_called_once_with(ok=True)


@pytest.mark.asyncio
async def test_handle_successful_payment(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = TelegramPaymentsAdapter()
    message = SimpleNamespace(
        successful_payment=SimpleNamespace(invoice_payload="payload"),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(message=message)
    context = SimpleNamespace()

    class DummyClient:
        def __init__(self) -> None:
            self.post = AsyncMock()

        async def __aenter__(self) -> DummyClient:  # type: ignore[override]
            return self

        async def __aexit__(self, *exc: object) -> None:  # type: ignore[override]
            return None

    dummy_client = DummyClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda: dummy_client)

    await adapter.handle_successful_payment(update, context)

    dummy_client.post.assert_called_once()
    message.reply_text.assert_called_once()
