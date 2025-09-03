"""Dummy billing provider used for tests and development."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import uuid4

from ...schemas.billing import WebhookEvent


MOCK_CHECKOUT_URL = "https://example.com/mock-checkout"


@dataclass
class DummyBillingProvider:
    """A simple provider that simulates successful payments."""

    test_mode: bool = True

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

    async def verify_webhook(self, event: WebhookEvent) -> bool:
        """Verify webhook signature and log the transaction."""

        logger = logging.getLogger(__name__)
        expected_sig = f"{event.event_id}:{event.transaction_id}"
        if event.signature != expected_sig:
            logger.info("webhook %s invalid_signature", event.transaction_id)
            return False
        logger.info("webhook %s verified", event.transaction_id)
        return True

    async def create_subscription(
        self, plan: str
    ) -> dict[str, str]:  # pragma: no cover - compat
        """Backward compatible alias for :meth:`create_checkout`."""

        return await self.create_checkout(plan)
