# test_config.py

import importlib
import sys
from types import ModuleType
from typing import Any, cast

import pytest


def _reload(module: str) -> ModuleType:
    if module in sys.modules:
        del sys.modules[module]
    return importlib.import_module(module)


def test_import_config_without_db_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    _reload("services.api.app.config")  # should not raise


def test_init_db_raises_when_no_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    config = cast(Any, _reload("services.api.app.config"))
    db = cast(Any, _reload("services.api.app.diabetes.services.db"))
    assert config.get_db_password() is None
    with pytest.raises(ValueError):
        db.init_db()
    db.init_db = lambda: None


def test_get_db_role_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DB_READ_PASSWORD", raising=False)
    monkeypatch.delenv("DB_WRITE_PASSWORD", raising=False)
    config = cast(Any, _reload("services.api.app.config"))
    assert config.get_db_read_password() is None
    assert config.get_db_write_password() is None
    monkeypatch.setenv("DB_READ_PASSWORD", "rpass")
    monkeypatch.setenv("DB_WRITE_PASSWORD", "wpass")
    assert config.get_db_read_password() == "rpass"
    assert config.get_db_write_password() == "wpass"


@pytest.mark.parametrize(
    ("origin", "ui_base", "path", "expected"),
    [
        (
            "https://example.com",
            "/ui",
            "/reminders/new",
            "https://example.com/ui/reminders/new",
        ),
        (
            "https://example.com/",
            "ui/",
            "reminders/new",
            "https://example.com/ui/reminders/new",
        ),
        (
            "https://example.com",
            "/ui",
            "reminders//new",
            "https://example.com/ui/reminders/new",
        ),
        (
            "https://example.com",
            "/ui",
            "reminders/new/",
            "https://example.com/ui/reminders/new/",
        ),
        (
            "https://example.com",
            "/ui",
            "",
            "https://example.com/ui/",
        ),
        (
            "https://example.com/base",
            "",
            "section?foo=1#top",
            "https://example.com/base/section?foo=1#top",
        ),
    ],
)
def test_build_ui_url_normalizes_path(
    monkeypatch: pytest.MonkeyPatch,
    origin: str,
    ui_base: str,
    path: str,
    expected: str,
) -> None:
    monkeypatch.setenv("PUBLIC_ORIGIN", origin)
    monkeypatch.setenv("UI_BASE_URL", ui_base)
    config = cast(Any, _reload("services.api.app.config"))
    try:
        url = config.build_ui_url(path)
        assert url == expected
        assert url.startswith(origin.rstrip("/"))
    finally:
        sys.modules.pop("services.api.app.config", None)


@pytest.mark.parametrize(
    "path",
    ["../admin", "/../admin", "reminders/../admin"],
)
def test_build_ui_url_rejects_parent_segments(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    config = cast(Any, _reload("services.api.app.config"))
    try:
        with pytest.raises(ValueError, match=r"\.\."):
            config.build_ui_url(path)
    finally:
        sys.modules.pop("services.api.app.config", None)


@pytest.mark.parametrize(
    "path",
    ["https://evil.com", "//evil.com", "http://evil.com/path"],
)
def test_build_ui_url_rejects_absolute_urls(
    monkeypatch: pytest.MonkeyPatch, path: str
) -> None:
    monkeypatch.setenv("PUBLIC_ORIGIN", "https://example.com")
    monkeypatch.setenv("UI_BASE_URL", "/ui")
    config = cast(Any, _reload("services.api.app.config"))
    try:
        with pytest.raises(ValueError, match="relative"):
            config.build_ui_url(path)
    finally:
        sys.modules.pop("services.api.app.config", None)
