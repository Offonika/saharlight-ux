"""Dummy billing provider used for tests and development."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4


@dataclass
class DummyBillingProvider:
    """A simple provider that simulates successful payments."""

    test_mode: bool = True

    async def create_payment(self) -> dict[str, object]:
        """Return a dummy successful payment response."""

        return {"status": "ok", "test_mode": self.test_mode}

    async def create_subscription(self, plan: str) -> dict[str, str]:
        """Return dummy checkout details for subscription creation."""

        checkout_id = f"chk_{uuid4().hex}"
        return {
            "id": checkout_id,
            "url": f"https://dummy/{plan}/{checkout_id}",
        }
