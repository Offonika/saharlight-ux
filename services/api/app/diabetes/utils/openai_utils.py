import asyncio
import atexit
import logging
import threading
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Literal, overload

import httpx
from openai import AsyncOpenAI, OpenAI

from services.api.app import config

logger = logging.getLogger(__name__)

_http_client: dict[str, httpx.Client] = {}
_http_client_lock = threading.Lock()

_async_http_client: dict[str, httpx.AsyncClient] = {}
_async_http_client_lock = threading.Lock()


@overload
def _build_http_client(
    proxy: str | None, async_: Literal[False]
) -> httpx.Client | None: ...


@overload
def _build_http_client(
    proxy: str | None, async_: Literal[True]
) -> httpx.AsyncClient | None: ...


def _build_http_client(
    proxy: str | None, async_: bool
) -> httpx.Client | httpx.AsyncClient | None:
    """Return an httpx client configured with optional proxy."""

    if proxy is None:
        return None

    if async_:
        global _async_http_client
        with _async_http_client_lock:
            async_client = _async_http_client.get(proxy)
            if async_client is None:
                async_client = httpx.AsyncClient(proxies=proxy)
                _async_http_client[proxy] = async_client
            return async_client

    global _http_client
    with _http_client_lock:
        sync_client = _http_client.get(proxy)
        if sync_client is None:
            sync_client = httpx.Client(proxies=proxy)
            _http_client[proxy] = sync_client
        return sync_client


def get_openai_client() -> OpenAI:
    """Return a configured OpenAI client.

    Configures an ``httpx`` client for proxy support and validates that
    required credentials are provided. The global environment is not
    mutated, keeping proxy settings local to the OpenAI client.
    """

    settings = config.get_settings()
    if not settings.openai_api_key:
        message = "OPENAI_API_KEY is not set"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    http_client = _build_http_client(settings.openai_proxy, False)
    client = OpenAI(api_key=settings.openai_api_key, http_client=http_client)

    if settings.openai_assistant_id:
        logger.info("[OpenAI] Using assistant: %s", settings.openai_assistant_id)
    return client


def get_async_openai_client() -> AsyncOpenAI:
    """Return a configured asynchronous OpenAI client."""

    settings = config.get_settings()
    if not settings.openai_api_key:
        message = "OPENAI_API_KEY is not set"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    http_client = _build_http_client(settings.openai_proxy, True)
    client = AsyncOpenAI(api_key=settings.openai_api_key, http_client=http_client)

    if settings.openai_assistant_id:
        logger.info("[OpenAI] Using assistant: %s", settings.openai_assistant_id)
    return client


async def dispose_http_client() -> None:
    """Close and reset the HTTP client used by OpenAI."""
    global _http_client, _async_http_client
    with _http_client_lock:
        for sync_client in _http_client.values():
            try:
                sync_client.close()
            except Exception:
                logger.exception("[OpenAI] Failed to close sync HTTP client")
        _http_client.clear()
    with _async_http_client_lock:
        for async_client in _async_http_client.values():
            try:
                await async_client.aclose()
            except Exception:
                logger.exception("[OpenAI] Failed to close async HTTP client")
        _async_http_client.clear()


@contextmanager
def openai_client_ctx() -> Iterator[OpenAI]:
    """Context manager yielding a configured OpenAI client.

    Ensures that the underlying HTTP client is disposed of when the
    context exits.
    """

    client = get_openai_client()
    try:
        yield client
    finally:
        try:
            loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is None:
            asyncio.run(dispose_http_client())
        else:
            loop.create_task(dispose_http_client())


@asynccontextmanager
async def async_openai_client_ctx() -> AsyncIterator[AsyncOpenAI]:
    """Async context manager yielding an asynchronous OpenAI client."""

    client = get_async_openai_client()
    try:
        yield client
    finally:
        await dispose_http_client()


def _dispose_http_client_sync() -> None:
    """Synchronously run ``dispose_http_client`` for ``atexit`` hooks."""

    try:
        asyncio.run(dispose_http_client())
    except Exception:  # pragma: no cover - best effort on shutdown
        logger.exception("[OpenAI] Failed to dispose HTTP client")


atexit.register(_dispose_http_client_sync)
