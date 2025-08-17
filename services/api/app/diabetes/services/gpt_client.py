# gpt_client.py

import asyncio
import logging
import os
import threading
from typing import Iterable

import httpx
from openai import NOT_GIVEN, NotGiven, OpenAI, OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.file_object import FileObject
from openai.types.beta import Thread
from openai.types.beta.threads import (
    ImageFileContentBlockParam,
    ImageURLContentBlockParam,
    Run,
    TextContentBlockParam,
)

from services.api.app.config import settings
from services.api.app.diabetes.utils.openai_utils import get_openai_client

logger = logging.getLogger(__name__)

_client: OpenAI | None = None
_client_lock = threading.Lock()


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = get_openai_client()
    return _client


def create_chat_completion(
    *,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
) -> ChatCompletion:
    """Create a chat completion with typed return value."""
    return _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        stream=False,
    )


async def create_thread() -> str:
    """Создаём пустой thread (ассистент задаётся позже, в runs.create).

    Returns
    -------
    str
        Идентификатор созданного thread.
    """
    client: OpenAI = _get_client()
    try:
        thread: Thread = await asyncio.to_thread(client.beta.threads.create)
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create thread: %s", exc)
        raise
    return thread.id


async def send_message(
    thread_id: str,
    content: str | None = None,
    image_path: str | None = None,
    *,
    keep_image: bool = False,
) -> Run:
    """Send text or (image + text) to the thread and start a run.

    Parameters
    ----------
    thread_id: str
        Target thread identifier.
    content: str | None
        Text message to send.  Must be provided if ``image_path`` is ``None``.
    image_path: str | None
        Path to an image to upload alongside the text.
    keep_image: bool, default ``False``
        If ``True`` the local file will not be removed after attempting the upload.

    Returns
    -------
    run
        The created run object.
    """
    if content is None and image_path is None:
        raise ValueError("Either 'content' or 'image_path' must be provided")

    # 1. Подготовка контента
    text_block: TextContentBlockParam = {
        "type": "text",
        "text": content if content is not None else "Что изображено на фото?",
    }
    client: OpenAI = _get_client()
    message_content: Iterable[
        ImageFileContentBlockParam | ImageURLContentBlockParam | TextContentBlockParam
    ]
    if image_path:
        try:

            def _upload() -> FileObject:
                with open(image_path, "rb") as f:
                    return client.files.create(file=f, purpose="vision")

            file = await asyncio.to_thread(_upload)
        except OSError as exc:
            logger.exception("[OpenAI] Failed to read %s: %s", image_path, exc)
            raise
        except OpenAIError as exc:
            logger.exception("[OpenAI] Failed to upload %s: %s", image_path, exc)
            raise
        else:
            logger.info("[OpenAI] Uploaded image %s, file_id=%s", image_path, file.id)
            image_block: ImageFileContentBlockParam = {
                "type": "image_file",
                "image_file": {"file_id": file.id},
            }
            message_content = [image_block, text_block]
            if not keep_image:
                try:
                    await asyncio.to_thread(os.remove, image_path)
                except OSError as e:
                    logger.warning("[OpenAI] Failed to delete %s: %s", image_path, e)
    else:
        message_content = [text_block]

    # 2. Создаём сообщение в thread
    try:
        await asyncio.to_thread(
            client.beta.threads.messages.create,
            thread_id=thread_id,
            role="user",
            content=message_content,
        )
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create message: %s", exc)
        raise

    if not settings.openai_assistant_id:
        message = "OPENAI_ASSISTANT_ID is not set"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    # 3. Запускаем ассистента
    try:
        run: Run = await asyncio.to_thread(
            client.beta.threads.runs.create,
            thread_id=thread_id,
            assistant_id=settings.openai_assistant_id,
        )
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create run: %s", exc)
        raise
    logger.debug("[OpenAI] Run %s started (thread %s)", run.id, thread_id)
    return run
