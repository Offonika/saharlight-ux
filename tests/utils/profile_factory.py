"""Factories for test profiles."""

from __future__ import annotations

from datetime import time

from services.api.app.diabetes.services.db import Profile


def make_profile(telegram_id: int = 1, **overrides: object) -> Profile:
    """Create a ``Profile`` instance with sensible defaults for tests."""

    data: dict[str, object] = {
        "telegram_id": telegram_id,
        "icr": 8.0,
        "cf": 3.0,
        "target_bg": 6.0,
        "low_threshold": 4.0,
        "high_threshold": 9.0,
        "sos_contact": "+123",
        "sos_alerts_enabled": True,
        "dia": 4.0,
        "round_step": 0.5,
        "carb_units": "g",
        "grams_per_xe": 12.0,
        "therapy_type": "insulin",
        "insulin_type": "rapid",
        "glucose_units": "mmol/L",
        "prebolus_min": 15,
        "max_bolus": 10.0,
        "postmeal_check_min": 120,
        "quiet_start": time(23, 0),
        "quiet_end": time(7, 0),
        "timezone": "UTC",
    }
    data.update(overrides)
    return Profile(**data)

