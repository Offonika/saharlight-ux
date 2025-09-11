import logging
import pytest

import services.bot.main as bot


def test_main_logs_persistence_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(bot.settings, "telegram_token", "token")
    monkeypatch.setattr(bot, "TELEGRAM_TOKEN", "token")
    monkeypatch.setattr(bot, "init_db", lambda: None)

    def faulty_build_persistence() -> object:
        raise RuntimeError("boom")

    monkeypatch.setattr(bot, "build_persistence", faulty_build_persistence)

    with caplog.at_level(logging.ERROR):
        with pytest.raises(SystemExit) as exc:
            bot.main()

    assert exc.value.code == 1
    assert any("STATE_DIRECTORY" in record.getMessage() for record in caplog.records)
