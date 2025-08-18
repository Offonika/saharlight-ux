import logging

import httpx
from openai import OpenAI

from services.api.app.config import settings

logger = logging.getLogger(__name__)


def get_openai_client() -> OpenAI:
    """Return a configured OpenAI client.

    Configures an ``httpx`` client for proxy support and validates that
    required credentials are provided. The global environment is not
    mutated, keeping proxy settings local to the OpenAI client.
    """

    if not settings.openai_api_key:
        message = "OPENAI_API_KEY is not set"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    client: OpenAI
    if settings.openai_proxy:
        with httpx.Client(proxies=settings.openai_proxy) as http_client:
            client = OpenAI(
                api_key=settings.openai_api_key, http_client=http_client
            )
    else:
        client = OpenAI(api_key=settings.openai_api_key, http_client=None)

    if settings.openai_assistant_id:
        logger.info("[OpenAI] Using assistant: %s", settings.openai_assistant_id)
    return client
