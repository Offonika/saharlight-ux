"""Utilities for parsing and validating user input for profile handlers."""

from __future__ import annotations


def parse_profile_args(args: list[str]) -> dict[str, str] | None:
    """Parse ``/profile`` command arguments into a dict."""
    if len(args) == 5 and all("=" not in a for a in args):
        return {
            "icr": args[0],
            "cf": args[1],
            "target": args[2],
            "low": args[3],
            "high": args[4],
        }

    parsed: dict[str, str] = {}
    for arg in args:
        if "=" not in arg:
            return None
        key, val = arg.split("=", 1)
        key = key.lower()
        match = None
        for full in ("icr", "cf", "target", "low", "high"):
            if full.startswith(key):
                match = full
                break
        if not match:
            return None
        parsed[match] = val
    if set(parsed) == {"icr", "cf", "target", "low", "high"}:
        return parsed
    return None
