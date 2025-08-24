import asyncio
import logging
import threading
from typing import Literal, overload

import httpx
from openai import AsyncOpenAI, OpenAI

from services.api.app import config

logger = logging.getLogger(__name__)

_http_client: httpx.Client | None = None
_http_client_lock = threading.Lock()

_async_http_client: httpx.AsyncClient | None = None
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
            if _async_http_client is None:
                _async_http_client = httpx.AsyncClient(proxies=proxy)
            return _async_http_client

    global _http_client
    with _http_client_lock:
        if _http_client is None:
            _http_client = httpx.Client(proxies=proxy)
        return _http_client


def get_openai_client() -> OpenAI:
    """Return a configured OpenAI client.

    Configures an ``httpx`` client for proxy support and validates that
    required credentials are provided. The global environment is not
    mutated, keeping proxy settings local to the OpenAI client.
    """

    if not config.settings.openai_api_key:
        message = "OPENAI_API_KEY is not set"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    http_client = _build_http_client(config.settings.openai_proxy, False)
    client = OpenAI(api_key=config.settings.openai_api_key, http_client=http_client)

    if config.settings.openai_assistant_id:
        logger.info("[OpenAI] Using assistant: %s", config.settings.openai_assistant_id)
    return client


def get_async_openai_client() -> AsyncOpenAI:
    """Return a configured asynchronous OpenAI client."""

    if not config.settings.openai_api_key:
        message = "OPENAI_API_KEY is not set"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    http_client = _build_http_client(config.settings.openai_proxy, True)
    client = AsyncOpenAI(
        api_key=config.settings.openai_api_key, http_client=http_client
    )

    if config.settings.openai_assistant_id:
        logger.info("[OpenAI] Using assistant: %s", config.settings.openai_assistant_id)
    return client


def dispose_http_client() -> None:
    """Close and reset the HTTP client used by OpenAI."""
    global _http_client, _async_http_client
    with _http_client_lock:
        if _http_client is not None:
            _http_client.close()
            _http_client = None
    with _async_http_client_lock:
        if _async_http_client is not None:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(_async_http_client.aclose())
            else:
                loop.create_task(_async_http_client.aclose())
            _async_http_client = None
