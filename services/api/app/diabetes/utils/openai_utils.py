import logging
import os
from openai import OpenAI
from services.api.app.config import OPENAI_API_KEY, OPENAI_ASSISTANT_ID, OPENAI_PROXY


def get_openai_client() -> OpenAI:
    """Return a configured OpenAI client.

    Sets proxy environment variables and validates that required
    credentials are provided.
    """
    if OPENAI_PROXY:
        os.environ["HTTP_PROXY"] = OPENAI_PROXY
        os.environ["HTTPS_PROXY"] = OPENAI_PROXY

    if not OPENAI_API_KEY:
        message = "OPENAI_API_KEY is not set"
        logging.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    client = OpenAI(api_key=OPENAI_API_KEY)
    if OPENAI_ASSISTANT_ID:
        logging.info("[OpenAI] Using assistant: %s", OPENAI_ASSISTANT_ID)
    return client
