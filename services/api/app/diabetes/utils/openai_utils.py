import logging
import os
from openai import OpenAI
from services.api.app.config import settings


def get_openai_client() -> OpenAI:
    """Return a configured OpenAI client.

    Sets proxy environment variables and validates that required
    credentials are provided.
    """
    if settings.openai_proxy:
        os.environ["HTTP_PROXY"] = settings.openai_proxy
        os.environ["HTTPS_PROXY"] = settings.openai_proxy

    if not settings.openai_api_key:
        message = "OPENAI_API_KEY is not set"
        logging.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    client = OpenAI(api_key=settings.openai_api_key)
    if settings.openai_assistant_id:
        logging.info("[OpenAI] Using assistant: %s", settings.openai_assistant_id)
    return client
