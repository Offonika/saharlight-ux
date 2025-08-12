from dataclasses import dataclass


@dataclass
class Profile:
    """Patient profile data used by handlers and tests."""

    telegram_id: int
    icr: float
    cf: float
    target: float
    low: float
    high: float
