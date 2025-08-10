"""Tests for webapp server startup checks."""

import importlib
import sys
from pathlib import Path

import pytest


def test_missing_ui_build_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Importing server without a built UI should raise an error."""
    ui_dir = (Path(__file__).resolve().parents[1] / "webapp" / "ui" / "dist").resolve()
    original_exists = Path.exists

    def fake_exists(self: Path) -> bool:  # noqa: ANN001
        if self == ui_dir:
            return False
        return original_exists(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    sys.modules.pop("webapp.server", None)
    with pytest.raises(RuntimeError):
        importlib.import_module("webapp.server")
    monkeypatch.setattr(Path, "exists", original_exists)
    importlib.import_module("webapp.server")

