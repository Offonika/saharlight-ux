from __future__ import annotations

import asyncio
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from services.bot.main import build_persistence, error_handler



def test_creates_writable_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    persistence_path = tmp_path / "state" / "data.pkl"
    monkeypatch.setenv("BOT_PERSISTENCE_PATH", str(persistence_path))

    persistence = build_persistence()

    assert persistence.filepath == persistence_path
    assert persistence_path.parent.exists()
    assert os.access(persistence_path.parent, os.W_OK)


def test_readonly_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    persistence_path = tmp_path / "ro" / "data.pkl"
    persistence_path.parent.mkdir()
    monkeypatch.setenv("BOT_PERSISTENCE_PATH", str(persistence_path))

    original_access = os.access

    def fake_access(path: str | bytes | os.PathLike[str] | os.PathLike[bytes], mode: int) -> bool:
        if Path(path) == persistence_path.parent:
            return False
        return original_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)

    with pytest.raises(RuntimeError) as excinfo:
        build_persistence()

    asyncio.run(error_handler("upd", SimpleNamespace(error=excinfo.value)))


def test_env_overrides(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_dir = tmp_path / "state"
    monkeypatch.setenv("STATE_DIRECTORY", str(state_dir))
    monkeypatch.delenv("BOT_PERSISTENCE_PATH", raising=False)

    persistence1 = build_persistence()
    assert persistence1.filepath == state_dir / "bot_persistence.pkl"

    override = tmp_path / "custom" / "persist.pkl"
    monkeypatch.setenv("BOT_PERSISTENCE_PATH", str(override))
    persistence2 = build_persistence()
    assert persistence2.filepath == override
