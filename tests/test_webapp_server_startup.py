"""Tests for API server startup checks."""

import importlib
from pathlib import Path

import pytest


def test_app_import_without_ui(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing services.api.app.main should succeed even if UI build is missing."""
    ui_dir = (Path(__file__).resolve().parents[1] / "webapp" / "ui" / "dist").resolve()
    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:  # noqa: ANN001
        if self == ui_dir:
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    importlib.reload(importlib.import_module("services.api.app.main"))

