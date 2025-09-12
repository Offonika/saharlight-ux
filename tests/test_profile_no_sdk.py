from types import SimpleNamespace
from typing import Any, cast

import builtins
import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from telegram import Update
from telegram.ext import CallbackContext

from services.api.app.config import Settings
from services.api.app.diabetes.services.db import Base, User, Profile


class DummyMessage:
    def __init__(self) -> None:
        self.texts: list[str] = []
        self.markups: list[Any] = []
        self.kwargs: list[dict[str, Any]] = []

    async def reply_text(
        self, text: str, **kwargs: Any
    ) -> None:  # pragma: no cover - simple helper
        self.texts.append(text)
        self.markups.append(kwargs.get("reply_markup"))
        self.kwargs.append(kwargs)

    async def delete(self) -> None:  # pragma: no cover - simple helper
        pass


def _patch_import(
    monkeypatch: pytest.MonkeyPatch, *, exc: type[Exception] = ImportError
) -> None:
    """Force ``exc`` for any ``diabetes_sdk`` imports."""

    real_import = builtins.__import__

    def fake_import(
        name: str,
        globals: Any = None,
        locals: Any = None,
        fromlist: Any = (),
        level: int = 0,
    ) -> Any:
        if name.startswith("diabetes_sdk"):
            raise exc("diabetes_sdk not available")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_get_api_falls_back_to_local_client(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """``get_api`` should provide a local client
    and log a warning on ``ImportError``."""

    _patch_import(monkeypatch)

    import importlib
    profile_api = importlib.import_module(
        "services.api.app.diabetes.handlers.profile.api"
    )

    monkeypatch.setattr(profile_api, "_sdk_warning_emitted", False)

    with caplog.at_level(logging.WARNING):
        api, exc, model = profile_api.get_api(
            settings=Settings(API_URL="http://example.org")
        )

    assert isinstance(api, profile_api.LocalProfileAPI)
    assert exc is Exception
    assert model is profile_api.LocalProfile
    assert "diabetes_sdk is not installed" in caplog.text


def test_get_api_handles_runtime_error(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """``get_api`` should fall back when ``RuntimeError`` occurs during import."""

    _patch_import(monkeypatch, exc=RuntimeError)

    import importlib
    profile_api = importlib.import_module(
        "services.api.app.diabetes.handlers.profile.api"
    )

    monkeypatch.setattr(profile_api, "_sdk_warning_emitted", False)

    with caplog.at_level(logging.WARNING):
        api, exc, model = profile_api.get_api(
            settings=Settings(API_URL="http://example.org")
        )

    assert isinstance(api, profile_api.LocalProfileAPI)
    assert exc is Exception
    assert model is profile_api.LocalProfile
    assert "could not be initialized" in caplog.text


def test_get_api_warns_only_once(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Repeated ``get_api`` calls should log the warning only once."""

    _patch_import(monkeypatch)

    import importlib
    profile_api = importlib.import_module(
        "services.api.app.diabetes.handlers.profile.api"
    )

    monkeypatch.setattr(profile_api, "_sdk_warning_emitted", False)

    with caplog.at_level(logging.WARNING):
        profile_api.get_api(settings=Settings(API_URL="http://example.org"))
        profile_api.get_api(settings=Settings(API_URL="http://example.org"))

    assert caplog.text.count("diabetes_sdk is not installed") == 1


@pytest.mark.asyncio
async def test_profile_command_and_view_without_sdk(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Profile commands should work even when ``diabetes_sdk`` is missing."""

    _patch_import(monkeypatch)
    monkeypatch.setenv("OPENAI_API_KEY", "test")
    monkeypatch.setenv("OPENAI_ASSISTANT_ID", "asst_test")
    monkeypatch.delenv("API_URL", raising=False)
    import services.api.app.config as config_module
    monkeypatch.setattr(config_module, "settings", Settings(_env_file=None))

    import importlib

    profile_api = importlib.import_module(
        "services.api.app.diabetes.handlers.profile.api"
    )
    from services.api.app.diabetes.handlers import profile as handlers

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    monkeypatch.setattr(handlers, "SessionLocal", TestSession)
    monkeypatch.setattr(profile_api, "SessionLocal", TestSession)

    with TestSession() as session:
        session.add(User(telegram_id=123, thread_id="t"))
        session.commit()

    msg = DummyMessage()
    update = cast(
        Update, SimpleNamespace(message=msg, effective_user=SimpleNamespace(id=123))
    )
    context = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(args=["8", "3", "6", "4", "9"], user_data={}),
    )

    with caplog.at_level(logging.WARNING):
        await handlers.profile_command(update, context)

    assert msg.texts and "ИКХ: 8.0 г/ед." in msg.texts[0]
    assert all("Функции профиля недоступны" not in t for t in msg.texts)

    with TestSession() as session:
        prof = session.get(Profile, 123)
        assert prof is not None
        assert prof.sos_contact is None
        assert prof.sos_alerts_enabled is True

    msg2 = DummyMessage()
    update2 = cast(
        Update, SimpleNamespace(message=msg2, effective_user=SimpleNamespace(id=123))
    )
    context2 = cast(
        CallbackContext[Any, dict[str, Any], dict[str, Any], dict[str, Any]],
        SimpleNamespace(user_data={}),
    )

    with caplog.at_level(logging.WARNING):
        await handlers.profile_view(update2, context2)

    assert msg2.texts and "ИКХ: 8.0 г/ед." in msg2.texts[0]
    assert all("Функции профиля недоступны" not in t for t in msg2.texts)
    assert "diabetes_sdk is not installed" not in caplog.text


def test_get_api_uses_local_when_no_api_url(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """No warning when API_URL isn't configured."""

    _patch_import(monkeypatch)
    monkeypatch.delenv("API_URL", raising=False)
    import services.api.app.config as config_module
    monkeypatch.setattr(config_module, "settings", Settings(_env_file=None))
    from services.api.app.diabetes.handlers.profile.api import (
        LocalProfileAPI,
        LocalProfile,
        get_api,
    )

    with caplog.at_level(logging.WARNING):
        api, exc, model = get_api(settings=config_module.settings)

    assert isinstance(api, LocalProfileAPI)
    assert exc is Exception
    assert model is LocalProfile
    assert "diabetes_sdk is not installed" not in caplog.text
