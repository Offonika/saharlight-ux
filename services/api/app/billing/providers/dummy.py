"""Dummy billing provider used for tests and development."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DummyBillingProvider:
    """A simple provider that simulates successful payments."""

    test_mode: bool = True

    async def create_payment(self) -> dict[str, object]:
        """Return a dummy successful payment response."""

        return {"status": "ok", "test_mode": self.test_mode}

