import asyncio
import atexit
import logging
import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final, TypeAlias

import httpx
from openai import AsyncOpenAI, OpenAI

from services.api.app import config

logger = logging.getLogger(__name__)

TimeoutKey: TypeAlias = tuple[float | None, float | None, float | None, float | None]
TimeoutInput: TypeAlias = httpx.Timeout | float

DEFAULT_HTTP_TIMEOUT: Final[httpx.Timeout] = httpx.Timeout(10.0)

_http_client: dict[tuple[str, TimeoutKey], httpx.Client] = {}
_http_client_lock = threading.Lock()

_async_http_client: dict[tuple[str, TimeoutKey], httpx.AsyncClient] = {}
_async_http_client_lock = threading.Lock()


def _resolve_timeout(timeout: TimeoutInput | None) -> tuple[httpx.Timeout, TimeoutKey]:
    """Return an ``httpx.Timeout`` instance and a hashable key representation."""

    if timeout is None:
        resolved_timeout = DEFAULT_HTTP_TIMEOUT
    elif isinstance(timeout, httpx.Timeout):
        resolved_timeout = timeout
    else:
        resolved_timeout = httpx.Timeout(float(timeout))

    timeout_key: TimeoutKey = (
        resolved_timeout.connect,
        resolved_timeout.read,
        resolved_timeout.write,
        resolved_timeout.pool,
    )
    return resolved_timeout, timeout_key


def build_http_client(
    proxy: str | None,
    timeout: TimeoutInput | None = None,
) -> httpx.Client | None:
    """Return a synchronous httpx client configured with optional proxy."""

    if proxy is None:
        return None

    global _http_client
    resolved_timeout, timeout_key = _resolve_timeout(timeout)
    key = (proxy, timeout_key)
    with _http_client_lock:
        client = _http_client.get(key)
        if client is None:
            client = httpx.Client(proxy=proxy, timeout=resolved_timeout)
            _http_client[key] = client
        return client


def build_async_http_client(
    proxy: str | None,
    timeout: TimeoutInput | None = None,
) -> httpx.AsyncClient | None:
    """Return an asynchronous httpx client configured with optional proxy."""

    if proxy is None:
        return None

    global _async_http_client
    resolved_timeout, timeout_key = _resolve_timeout(timeout)
    key = (proxy, timeout_key)
    with _async_http_client_lock:
        client = _async_http_client.get(key)
        if client is None:
            client = httpx.AsyncClient(proxy=proxy, timeout=resolved_timeout)
            _async_http_client[key] = client
        return client


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

    http_client = build_http_client(settings.openai_proxy)
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

    http_client = build_async_http_client(settings.openai_proxy)
    client = AsyncOpenAI(api_key=settings.openai_api_key, http_client=http_client)

    if settings.openai_assistant_id:
        logger.info("[OpenAI] Using assistant: %s", settings.openai_assistant_id)
    return client


async def dispose_http_client() -> None:
    """Close and reset the HTTP client used by OpenAI."""
    global _http_client, _async_http_client

    # Gather and clear synchronous clients under lock, then close outside the lock
    with _http_client_lock:
        sync_clients = list(_http_client.values())
        _http_client.clear()
    for sync_client in sync_clients:
        try:
            sync_client.close()
        except Exception:  # pragma: no cover - best effort
            logger.exception("[OpenAI] Failed to close HTTP client")

    # Gather and clear asynchronous clients under lock, then close outside the lock
    with _async_http_client_lock:
        async_clients = list(_async_http_client.values())
        _async_http_client.clear()
    for async_client in async_clients:
        try:
            await async_client.aclose()
        except Exception:  # pragma: no cover - best effort
            logger.exception("[OpenAI] Failed to close HTTP client")


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
            client.close()
        except Exception:  # pragma: no cover - best effort on shutdown
            logger.exception("[OpenAI] Failed to close client")

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
            await client.close()
        except Exception:  # pragma: no cover - best effort on shutdown
            logger.exception("[OpenAI] Failed to close client")

        try:
            await dispose_http_client()
        except Exception:  # pragma: no cover - best effort on shutdown
            logger.exception("[OpenAI] Failed to dispose HTTP client")


def _dispose_http_client_sync() -> None:
    """Synchronously run ``dispose_http_client`` for ``atexit`` hooks."""

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        try:
            with asyncio.Runner() as runner:
                runner.run(dispose_http_client())
        except Exception:  # pragma: no cover - best effort on shutdown
            logger.exception("[OpenAI] Failed to dispose HTTP client")
    else:
        loop.create_task(dispose_http_client())


atexit.register(_dispose_http_client_sync)
