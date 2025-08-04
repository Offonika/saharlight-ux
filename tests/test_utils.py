# test_utils.py

import asyncio
import io
import time

import pytest

from diabetes import utils
from diabetes.utils import clean_markdown, split_text_by_width

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
