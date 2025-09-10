from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from telegram.ext import Application, CallbackContext, ExtBot, PicklePersistence


@pytest.mark.asyncio
async def test_tg_init_data_persisted_after_restart(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    persistence_path = tmp_path / "data.pkl"

    async def dummy_initialize(self: ExtBot) -> None:
        return None

    async def dummy_shutdown(self: ExtBot) -> None:
        return None

    monkeypatch.setattr(ExtBot, "initialize", dummy_initialize)
    monkeypatch.setattr(ExtBot, "shutdown", dummy_shutdown)

    persistence1 = PicklePersistence(str(persistence_path), single_file=True)
    app1 = Application.builder().token("TOKEN").persistence(persistence1).build()
    await app1.initialize()

    app1.user_data[1]["tg_init_data"] = "abc"
    await app1.persistence.update_user_data(1, app1.user_data[1])
    await app1.persistence.flush()

    persistence2 = PicklePersistence(str(persistence_path), single_file=True)
    app2 = Application.builder().token("TOKEN").persistence(persistence2).build()
    await app2.initialize()

    ctx2: CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]] = CallbackContext(app2, user_id=1)
    assert ctx2.user_data["tg_init_data"] == "abc"
