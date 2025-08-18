# test_utils.py
from typing import Any, ContextManager, Literal


import asyncio
import io
import time
import logging
from datetime import timedelta
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

import pytest

import services.api.app.diabetes.utils.helpers as utils
from services.api.app.diabetes.utils.helpers import (
    clean_markdown,
    parse_time_interval,
    split_text_by_width,
)


def test_clean_markdown() -> None:
    text = (
        "**Жирный** __подчёркнутый__ _курсив_ *italic* "
        "[ссылка](http://example.com) ![alt](img.png) `код` ~~зачёркнуто~~\n"
        "# Заголовок\n* элемент\n1. Первый"
    )
    cleaned = clean_markdown(text)
    assert "Жирный" in cleaned
    assert "подчёркнутый" in cleaned
    assert "курсив" in cleaned
    assert "italic" in cleaned
    assert "ссылка" in cleaned
    assert "alt" in cleaned
    assert "код" in cleaned
    assert "зачёркнуто" in cleaned
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "1." not in cleaned
    assert "__" not in cleaned
    assert "_" not in cleaned
    assert "~~" not in cleaned


def test_split_text_by_width_simple() -> None:
    text = "Это короткая строка"
    pdfmetrics.registerFont(
        TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    )
    lines = split_text_by_width(text, "DejaVuSans", 12, 50)
    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)


@pytest.mark.parametrize(
    "text",
    [
        "Supercalifragilisticexpialidocious",
        "Hello Supercalifragilisticexpialidocious world",
    ],
)
def test_split_text_by_width_respects_limit(text: Any) -> None:
    pdfmetrics.registerFont(
        TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    )
    max_width = 20
    lines = split_text_by_width(text, "DejaVuSans", 12, max_width)
    for line in lines:
        assert stringWidth(line, "DejaVuSans", 12) / mm <= max_width


@pytest.mark.asyncio
async def test_get_coords_and_link_non_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def slow_urlopen(*args: object, **kwargs: object) -> ContextManager[io.StringIO]:
        time.sleep(0.2)

        class Resp:
            def __enter__(self) -> io.StringIO:
                return io.StringIO('{"loc": "1,2"}')

            def __exit__(
                self, exc_type: object, exc: object, tb: object
            ) -> Literal[False]:
                return False

        return Resp()

    monkeypatch.setattr(utils, "urlopen", slow_urlopen)

    start = time.perf_counter()
    task = asyncio.create_task(utils.get_coords_and_link())
    await asyncio.sleep(0.05)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.2
    assert await task == ("1,2", "https://maps.google.com/?q=1,2")


@pytest.mark.asyncio
async def test_get_coords_and_link_logs_warning(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def failing_urlopen(*args: object, **kwargs: object) -> None:
        raise OSError("network down")

    monkeypatch.setattr(utils, "urlopen", failing_urlopen)

    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link()

    assert coords is None and link is None
    assert any("Failed to fetch coordinates" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_get_coords_and_link_invalid_loc(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    def bad_urlopen(*args: object, **kwargs: object) -> ContextManager[io.StringIO]:
        class Resp:
            def __enter__(self) -> io.StringIO:
                return io.StringIO('{"loc": "invalid"}')

            def __exit__(
                self, exc_type: object, exc: object, tb: object
            ) -> Literal[False]:
                return False

        return Resp()

    monkeypatch.setattr(utils, "urlopen", bad_urlopen)

    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link()

    assert coords is None and link is None
    assert any("Invalid location format" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_get_coords_and_link_custom_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(url: str, timeout: int = 5) -> ContextManager[io.StringIO]:
        assert url == "http://custom"

        class Resp:
            def __enter__(self) -> io.StringIO:
                return io.StringIO('{"loc": "1,2"}')

            def __exit__(
                self, exc_type: object, exc: object, tb: object
            ) -> Literal[False]:
                return False

        return Resp()

    monkeypatch.setattr(utils, "urlopen", fake_urlopen)

    coords, link = await utils.get_coords_and_link("http://custom")
    assert coords == "1,2"
    assert link == "https://maps.google.com/?q=1,2"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5H", timedelta(hours=5)),
        ("3D", timedelta(days=3)),
    ],
)
def test_parse_interval_uppercase(text: Any, expected: Any) -> None:
    assert parse_time_interval(text) == expected
