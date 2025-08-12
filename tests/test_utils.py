# test_utils.py

import asyncio
import io
import time
import logging
from datetime import timedelta
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import pytest

import services.api.app.diabetes.utils.helpers as utils
from services.api.app.diabetes.utils.helpers import clean_markdown, parse_time_interval, split_text_by_width

def test_clean_markdown():
    text = "**Жирный**\n# Заголовок\n* элемент\n1. Первый"
    cleaned = clean_markdown(text)
    assert "Жирный" in cleaned
    assert "Заголовок" in cleaned
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "1." not in cleaned

def test_split_text_by_width_simple():
    text = "Это короткая строка"
    pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    lines = split_text_by_width(text, "DejaVuSans", 12, 50)
    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)


@pytest.mark.asyncio
async def test_get_coords_and_link_non_blocking(monkeypatch):
    def slow_urlopen(*args, **kwargs):
        time.sleep(0.2)

        class Resp:
            def __enter__(self):
                return io.StringIO('{"loc": "1,2"}')

            def __exit__(self, exc_type, exc, tb):
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
async def test_get_coords_and_link_logs_warning(monkeypatch, caplog):
    def failing_urlopen(*args, **kwargs):
        raise OSError("network down")

    monkeypatch.setattr(utils, "urlopen", failing_urlopen)

    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link()

    assert coords is None and link is None
    assert any("Failed to fetch coordinates" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_get_coords_and_link_invalid_loc(monkeypatch, caplog):
    def bad_urlopen(*args, **kwargs):
        class Resp:
            def __enter__(self):
                return io.StringIO('{"loc": "invalid"}')

            def __exit__(self, exc_type, exc, tb):
                return False

        return Resp()

    monkeypatch.setattr(utils, "urlopen", bad_urlopen)

    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link()

    assert coords is None and link is None
    assert any("Invalid location format" in msg for msg in caplog.messages)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5H", timedelta(hours=5)),
        ("3D", timedelta(days=3)),
    ],
)
def test_parse_interval_uppercase(text, expected):
    assert parse_time_interval(text) == expected
