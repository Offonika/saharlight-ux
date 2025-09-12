import asyncio
import atexit
import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
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
            sync_client.close()
        _http_client.clear()
    with _async_http_client_lock:
        for async_client in _async_http_client.values():
            await async_client.aclose()
        _async_http_client.clear()


@asynccontextmanager
async def openai_client_ctx() -> AsyncIterator[OpenAI]:
    """Context manager yielding a configured OpenAI client.

    Ensures that the underlying HTTP client is disposed of when the
    context exits. Disposes the underlying HTTP client either by
    awaiting in an active event loop or by running a new loop when
    called from synchronous code.
    """

    client = get_openai_client()
    try:
        yield client
    finally:
        try:
            loop: asyncio.AbstractEventLoop | None = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        try:
            if loop is None:
                asyncio.run(dispose_http_client())
            else:
                await dispose_http_client()
        except Exception:  # pragma: no cover - best effort on shutdown
            logger.exception("[OpenAI] Failed to dispose HTTP client")


@asynccontextmanager
async def async_openai_client_ctx() -> AsyncIterator[AsyncOpenAI]:
    """Async context manager yielding an asynchronous OpenAI client."""

    client = get_async_openai_client()
    try:
        yield client
    finally:
        try:
            await dispose_http_client()
        except Exception:  # pragma: no cover - best effort on shutdown
            logger.exception("[OpenAI] Failed to dispose HTTP client")


def _dispose_http_client_sync() -> None:
    """Synchronously run ``dispose_http_client`` for ``atexit`` hooks."""

    loop: asyncio.AbstractEventLoop
    created_loop = False
    previous_loop: asyncio.AbstractEventLoop | None = None
    try:
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                raise RuntimeError
        except RuntimeError:
            try:
                previous_loop = asyncio.get_event_loop()
            except RuntimeError:
                previous_loop = None
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            created_loop = True

        loop.run_until_complete(dispose_http_client())
    except Exception:  # pragma: no cover - best effort on shutdown
        logger.exception("[OpenAI] Failed to dispose HTTP client")
    finally:
        if created_loop:
            loop.close()
            asyncio.set_event_loop(previous_loop)


atexit.register(_dispose_http_client_sync)
