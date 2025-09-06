from __future__ import annotations

import hashlib
import hmac
import logging
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

    await adapter.create_invoice(update, context, plan="pro")

    bot.send_invoice.assert_called_once()
    assert bot.send_invoice.call_args.kwargs["payload"] == "pro"


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
    secret = "topsecret"
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", secret)
    adapter = TelegramPaymentsAdapter()
    message = SimpleNamespace(
        successful_payment=SimpleNamespace(
            invoice_payload="pro",
            telegram_payment_charge_id="evt1",
            provider_payment_charge_id="txn1",
        ),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(message=message)

    captured: dict[str, object] = {}

    async def _post(url: str, json: object, headers: dict[str, str]) -> SimpleNamespace:
        captured["url"] = url
        captured["json"] = json
        captured["headers"] = headers
        return SimpleNamespace(status_code=200, text="ok")

    class DummyClient:
        def __init__(self) -> None:
            self.post = AsyncMock(side_effect=_post)

        async def __aenter__(self) -> DummyClient:  # type: ignore[override]
            return self

        async def __aexit__(self, *exc: object) -> None:  # type: ignore[override]
            return None

    dummy_client = DummyClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda: dummy_client)

    await adapter.handle_successful_payment(update, SimpleNamespace())

    sig = hmac.new(secret.encode(), b"evt1:txn1:pro", hashlib.sha256).hexdigest()
    assert captured["json"] == {
        "event_id": "evt1",
        "transaction_id": "txn1",
        "plan": "pro",
        "signature": sig,
    }
    assert captured["headers"] == {"X-Webhook-Signature": sig}
    message.reply_text.assert_called_once_with("✅ Платёж успешно получен")


@pytest.mark.asyncio
async def test_handle_successful_payment_logs_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", "s")
    adapter = TelegramPaymentsAdapter()
    message = SimpleNamespace(
        successful_payment=SimpleNamespace(
            invoice_payload="pro",
            telegram_payment_charge_id="evt2",
            provider_payment_charge_id="txn2",
        ),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(message=message)

    async def _post(url: str, json: object, headers: dict[str, str]) -> SimpleNamespace:
        return SimpleNamespace(status_code=500, text="boom")

    class DummyClient:
        def __init__(self) -> None:
            self.post = AsyncMock(side_effect=_post)

        async def __aenter__(self) -> DummyClient:  # type: ignore[override]
            return self

        async def __aexit__(self, *exc: object) -> None:  # type: ignore[override]
            return None

    dummy_client = DummyClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda: dummy_client)

    caplog.set_level(logging.ERROR)
    await adapter.handle_successful_payment(update, SimpleNamespace())

    assert any("billing webhook" in r.getMessage() for r in caplog.records)
    message.reply_text.assert_called_once_with(
        "⚠️ Не удалось подтвердить платёж, попробуйте позже",
    )


@pytest.mark.asyncio
async def test_handle_successful_payment_http_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("BILLING_WEBHOOK_SECRET", "s")
    adapter = TelegramPaymentsAdapter()
    message = SimpleNamespace(
        successful_payment=SimpleNamespace(
            invoice_payload="pro",
            telegram_payment_charge_id="evt3",
            provider_payment_charge_id="txn3",
        ),
        reply_text=AsyncMock(),
    )
    update = SimpleNamespace(message=message)

    async def _post(url: str, json: object, headers: dict[str, str]) -> SimpleNamespace:
        raise httpx.HTTPError("boom")

    class DummyClient:
        def __init__(self) -> None:
            self.post = AsyncMock(side_effect=_post)

        async def __aenter__(self) -> DummyClient:  # type: ignore[override]
            return self

        async def __aexit__(self, *exc: object) -> None:  # type: ignore[override]
            return None

    dummy_client = DummyClient()
    monkeypatch.setattr(httpx, "AsyncClient", lambda: dummy_client)

    caplog.set_level(logging.ERROR)
    await adapter.handle_successful_payment(update, SimpleNamespace())

    assert any("billing webhook" in r.getMessage() for r in caplog.records)
    message.reply_text.assert_called_once_with(
        "⚠️ Не удалось подтвердить платёж, попробуйте позже",
    )
