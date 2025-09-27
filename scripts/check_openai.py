#!/usr/bin/env python3
"""Minimal smoke test for OPENAI_API_KEY configuration."""

from __future__ import annotations

import os
import sys

import httpx

DEFAULT_BASE_URL = "https://api.openai.com"


def _build_models_url(base_url: str) -> str:
    normalized = base_url.rstrip("/") or DEFAULT_BASE_URL
    return f"{normalized}/v1/models"


def main() -> int:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", DEFAULT_BASE_URL)

    if not api_key:
        print("OPENAI_API_KEY is not set")
        return 1

    try:
        response = httpx.get(
            _build_models_url(base_url),
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        print(f"FAIL network error: {exc}")
        return 1

    if response.is_success:
        print("OK")
        return 0

    print(f"FAIL {response.status_code}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
