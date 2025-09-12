from typing import Any, AsyncIterator, cast


import asyncio
import time
import logging
from datetime import timedelta
import pytest
import pytest_asyncio

import httpx

import services.api.app.diabetes.utils.helpers as utils
from services.api.app.diabetes.utils.helpers import parse_time_interval


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_geo_client() -> AsyncIterator[None]:
    yield
    await utils.dispose_geo_client()


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
async def test_get_coords_and_link_invalid_float(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    async def bad_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "1,invalid"}

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
        assert url == "http://ipinfo.io/custom"

        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "1,2"}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    coords, link = await utils.get_coords_and_link("http://ipinfo.io/custom")
    assert coords == "1,2"
    assert link == "https://maps.google.com/?q=1,2"


@pytest.mark.asyncio
async def test_get_coords_and_link_env_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        calls.append(url)

        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "1,2"}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.delenv("GEO_DATA_URL", raising=False)

    await utils.get_coords_and_link()
    assert calls[-1] == "https://ipinfo.io/json"

    monkeypatch.setenv("GEO_DATA_URL", "http://ipinfo.io/env")
    await utils.get_coords_and_link()
    assert calls[-1] == "http://ipinfo.io/env"


@pytest.mark.asyncio
async def test_get_coords_and_link_invalid_scheme(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link("ftp://ipinfo.io/json")

    assert coords is None and link is None
    assert any("Invalid source URL" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_get_coords_and_link_invalid_host(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING):
        coords, link = await utils.get_coords_and_link("https://example.com/json")

    assert coords is None and link is None
    assert any("Invalid source URL" in msg for msg in caplog.messages)


@pytest.mark.asyncio
async def test_get_coords_and_link_mixed_case_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_get(self: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
        class Resp:
            status_code = 200
            headers = {"Content-Type": "application/json"}

            def raise_for_status(self) -> None:  # pragma: no cover - dummy
                pass

            def json(self) -> dict[str, str]:
                return {"loc": "1,2"}

        return Resp()

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    coords, link = await utils.get_coords_and_link("https://IPInfo.io/json")
    assert coords == "1,2"
    assert link == "https://maps.google.com/?q=1,2"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "content_type",
    ["application/json", "Application/Json", "APPLICATION/JSON"],
)
async def test_get_coords_and_link_content_type_case(monkeypatch: pytest.MonkeyPatch, content_type: str) -> None:
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


@pytest.mark.asyncio
async def test_dispose_geo_client() -> None:
    closed = False

    class DummyClient:
        async def aclose(self) -> None:
            nonlocal closed
            closed = True

    async with utils._geo_client_lock:
        utils._geo_client = cast(httpx.AsyncClient, DummyClient())

    await utils.dispose_geo_client()
    assert closed
    assert utils._geo_client is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("5H", timedelta(hours=5)),
        ("3D", timedelta(days=3)),
    ],
)
def test_parse_interval_uppercase(text: Any, expected: Any) -> None:
    assert parse_time_interval(text) == expected
