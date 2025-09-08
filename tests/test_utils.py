# test_utils.py
from typing import Any


import asyncio
import time
import logging
from datetime import timedelta
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.lib.units import mm

import pytest

import httpx

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
        "# Заголовок\n* элемент\n- минус\n+ плюс\n1. Первый"
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
    assert "минус" in cleaned
    assert "плюс" in cleaned
    assert "#" not in cleaned
    assert "*" not in cleaned
    assert "-" not in cleaned
    assert "+" not in cleaned
    assert "1." not in cleaned
    assert "__" not in cleaned
    assert "_" not in cleaned
    assert "~~" not in cleaned


def test_split_text_by_width_simple() -> None:
    text = "Это короткая строка"
    pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    lines = split_text_by_width(text, "DejaVuSans", 12, 50)
    assert isinstance(lines, list)
    assert all(isinstance(line, str) for line in lines)


def test_split_text_by_width_unknown_font() -> None:
    with pytest.raises(ValueError, match="Unknown font"):
        split_text_by_width("text", "NoSuchFont", 12, 50)


@pytest.mark.parametrize(
    ("font_size", "max_width"),
    [
        (0, 50),
        (12, 0),
        (-1, 50),
        (12, -5),
    ],
)
def test_split_text_by_width_invalid_params(font_size: float, max_width: float) -> None:
    pdfmetrics.registerFont(
        TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    )
    with pytest.raises(ValueError, match="must be positive"):
        split_text_by_width("text", "DejaVuSans", font_size, max_width)


@pytest.mark.parametrize(
    "text",
    [
        "Supercalifragilisticexpialidocious",
        "Hello Supercalifragilisticexpialidocious world",
    ],
)
def test_split_text_by_width_respects_limit(text: Any) -> None:
    pdfmetrics.registerFont(TTFont("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    max_width = 20
    lines = split_text_by_width(text, "DejaVuSans", 12, max_width)
    for line in lines:
        assert stringWidth(line, "DejaVuSans", 12) / mm <= max_width


@pytest.mark.asyncio
async def test_get_coords_and_link_non_blocking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def slow_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        await asyncio.sleep(0.2)

        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "1,2"}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", slow_get)

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
    async def failing_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        raise httpx.HTTPError("network down")

    monkeypatch.setattr(httpx.AsyncClient, "get", failing_get)

    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link()

    assert coords is None and link is None
    assert any("Failed to fetch coordinates" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_get_coords_and_link_invalid_loc(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def bad_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "invalid"}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", bad_get)

    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link()

    assert coords is None and link is None
    assert any("Invalid location format" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_get_coords_and_link_custom_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        assert url == "http://custom"

        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "1,2"}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    coords, link = await utils.get_coords_and_link("http://custom")
    assert coords == "1,2"
    assert link == "https://maps.google.com/?q=1,2"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_type",
    ["application/json", "Application/Json", "APPLICATION/JSON"],
)
async def test_get_coords_and_link_content_type_case(
    monkeypatch: pytest.MonkeyPatch, content_type: str
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        class Resp:
            status_code = 200
            headers = {"Content-Type": content_type}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "1,2"}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    coords, link = await utils.get_coords_and_link()
    assert coords == "1,2"
    assert link == "https://maps.google.com/?q=1,2"


@pytest.mark.asyncio
async def test_get_coords_and_link_strips_coords(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": " 1 , 2 "}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    coords, link = await utils.get_coords_and_link()
    assert coords == "1,2"
    assert link == "https://maps.google.com/?q=1,2"


@pytest.mark.asyncio
async def test_get_coords_and_link_non_str_loc(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, Any]:
                return {"loc": ["1", "2"]}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

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
def test_parse_interval_uppercase(text: Any, expected: Any) -> None:
    assert parse_time_interval(text) == expected
