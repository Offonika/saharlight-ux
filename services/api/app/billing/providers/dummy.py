"""Dummy billing provider used for tests and development."""

from __future__ import annotations

import logging
import hmac
import hashlib
from dataclasses import dataclass
from uuid import uuid4

from ...schemas.billing import WebhookEvent


MOCK_CHECKOUT_URL = "https://example.com/mock-checkout"


@dataclass
class DummyBillingProvider:
    """A simple provider that simulates successful payments."""

    test_mode: bool = True
    webhook_secret: str | None = None

    async def create_payment(self) -> dict[str, object]:
        """Return a dummy successful payment response."""

        return {"status": "ok", "test_mode": self.test_mode}

    async def create_checkout(self, plan: str) -> dict[str, str]:
        """Return dummy checkout details for subscription creation."""

        checkout_id = f"chk_{uuid4().hex}"
        logger = logging.getLogger(__name__)
        logger.info("create_checkout %s", checkout_id)
        return {
            "id": checkout_id,
            "url": f"{MOCK_CHECKOUT_URL}?plan={plan}&transaction={checkout_id}",
        }

    async def verify_webhook(self, event: WebhookEvent, signature: str) -> bool:
        """Verify webhook signature and log the transaction."""

        logger = logging.getLogger(__name__)
        msg = f"{event.event_id}:{event.transaction_id}".encode()
        if self.webhook_secret:
            expected_sig = hmac.new(
                self.webhook_secret.encode(), msg, hashlib.sha256
            ).hexdigest()
        else:
            expected_sig = msg.decode()
        if not hmac.compare_digest(signature, expected_sig):
            logger.info("webhook %s invalid_signature", event.transaction_id)
            return False
        logger.info("webhook %s verified", event.transaction_id)
        return True

    async def create_subscription(
        self, plan: str
    ) -> dict[str, str]:  # pragma: no cover - compat
        """Backward compatible alias for :meth:`create_checkout`."""

        return await self.create_checkout(plan)
