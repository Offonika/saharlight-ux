# gpt_client.py

import asyncio
import io
import logging
import threading
from typing import Iterable

import httpx
from openai import AsyncOpenAI, NOT_GIVEN, NotGiven, OpenAI, OpenAIError
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam
from openai.types.file_object import FileObject
from openai.types.beta import Thread
from openai.types.beta.threads import (
    ImageFileContentBlockParam,
    ImageURLContentBlockParam,
    Run,
    TextContentBlockParam,
)

from services.api.app import config
from services.api.app.diabetes.llm_router import LLMRouter, LLMTask
from services.api.app.diabetes.utils.openai_utils import (
    get_async_openai_client,
    get_openai_client,
)

logger = logging.getLogger(__name__)

FILE_UPLOAD_TIMEOUT = 30.0
THREAD_CREATION_TIMEOUT = 30.0
MESSAGE_CREATION_TIMEOUT = 30.0
RUN_CREATION_TIMEOUT = 30.0

_client: OpenAI | None = None
_client_lock = threading.Lock()

_async_client: AsyncOpenAI | None = None
_async_client_lock: asyncio.Lock | None = None

_learning_router = LLMRouter()


def _get_client() -> OpenAI:
    """Return cached OpenAI client, creating it once in a thread-safe manner."""
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = get_openai_client()
    return _client


async def _get_async_client() -> AsyncOpenAI:
    """Return cached AsyncOpenAI client, creating it once in an async-safe manner."""
    global _async_client
    if _async_client is None:
        global _async_client_lock
        if _async_client_lock is None:
            _async_client_lock = asyncio.Lock()
        async with _async_client_lock:
            if _async_client is None:
                _async_client = get_async_openai_client()
    return _async_client


async def dispose_openai_clients() -> None:
    """Close and reset cached OpenAI clients."""
    global _client, _async_client
    with _client_lock:
        if _client is not None:
            _client.close()
            _client = None
    global _async_client_lock
    if _async_client_lock is None:
        _async_client_lock = asyncio.Lock()
    async with _async_client_lock:
        if _async_client is not None:
            await _async_client.close()
            _async_client = None


async def create_chat_completion(
    *,
    model: str,
    messages: Iterable[ChatCompletionMessageParam],
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
) -> ChatCompletion:
    """Create a chat completion with typed return value."""
    client: AsyncOpenAI = await _get_async_client()
    return await client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        stream=False,
    )


async def create_learning_chat_completion(
    *,
    task: LLMTask,
    messages: Iterable[ChatCompletionMessageParam],
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float | httpx.Timeout | None | NotGiven = NOT_GIVEN,
) -> ChatCompletion:
    """Create a chat completion for learning tasks using the model router."""
    model = _learning_router.choose_model(task)
    return await create_chat_completion(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
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
        thread: Thread = await asyncio.wait_for(
            asyncio.to_thread(client.beta.threads.create),
            timeout=THREAD_CREATION_TIMEOUT,
        )
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create thread: %s", exc)
        raise
    except asyncio.TimeoutError:
        message = "Thread creation timed out"
        logger.exception("[OpenAI] %s", message)
        raise RuntimeError(message)
    return thread.id


async def _upload_image_file(client: OpenAI, image_path: str) -> FileObject:
    """Upload an image from filesystem and return the created file object."""
    try:

        def _upload() -> FileObject:
            with open(image_path, "rb") as f:
                return client.files.create(file=f, purpose="vision")

        file = await asyncio.wait_for(
            asyncio.to_thread(_upload), timeout=FILE_UPLOAD_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.exception("[OpenAI] Timeout while uploading %s", image_path)
        raise RuntimeError("Timed out while uploading image")
    except OSError as exc:
        logger.exception("[OpenAI] Failed to read %s: %s", image_path, exc)
        raise
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to upload %s: %s", image_path, exc)
        raise
    else:
        logger.info("[OpenAI] Uploaded image %s, file_id=%s", image_path, file.id)
        return file


async def _upload_image_bytes(client: OpenAI, image_bytes: bytes) -> FileObject:
    """Upload raw image bytes and return the created file object."""
    try:

        def _upload_bytes() -> FileObject:
            with io.BytesIO(image_bytes) as buffer:
                return client.files.create(file=("image.jpg", buffer), purpose="vision")

        file = await asyncio.wait_for(
            asyncio.to_thread(_upload_bytes), timeout=FILE_UPLOAD_TIMEOUT
        )
    except asyncio.TimeoutError:
        logger.exception("[OpenAI] Timeout while uploading bytes")
        raise RuntimeError("Timed out while uploading image")
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to upload image bytes: %s", exc)
        raise
    else:
        logger.info("[OpenAI] Uploaded image from bytes, file_id=%s", file.id)
        return file


async def send_message(
    thread_id: str,
    content: str | None = None,
    image_path: str | None = None,
    image_bytes: bytes | None = None,
) -> Run:
    """Send text or (image + text) to the thread and start a run.

    Parameters
    ----------
    thread_id: str
        Target thread identifier.
    content: str | None
        Text message to send.  Must be provided if no image is supplied.
    image_path: str | None
        Path to an image to upload alongside the text.
    image_bytes: bytes | None
        Raw image bytes to upload instead of a file path.

    Returns
    -------
    run
        The created run object.

    Examples
    --------
    Send only an image and let the default prompt be used:

    >>> await send_message(thread_id="abc", image_path="/tmp/photo.jpg")
    """
    if content is None and image_path is None and image_bytes is None:
        raise ValueError("Either 'content' or image must be provided")
    if image_path is not None and image_bytes is not None:
        raise ValueError("Specify only one of 'image_path' or 'image_bytes'")

    settings = config.get_settings()
    if not settings.openai_assistant_id:
        message = "OPENAI_ASSISTANT_ID is not set"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)

    client: OpenAI = _get_client()

    # 1. Подготовка контента
    text_block: TextContentBlockParam = {
        "type": "text",
        "text": content if content is not None else "Что изображено на фото?",
    }
    message_content: Iterable[
        ImageFileContentBlockParam | ImageURLContentBlockParam | TextContentBlockParam
    ]
    if image_path:
        file = await _upload_image_file(client, image_path)
        image_block: ImageFileContentBlockParam = {
            "type": "image_file",
            "image_file": {"file_id": file.id},
        }
        message_content = [image_block, text_block]
    elif image_bytes is not None:
        file = await _upload_image_bytes(client, image_bytes)
        image_block: ImageFileContentBlockParam = {
            "type": "image_file",
            "image_file": {"file_id": file.id},
        }
        message_content = [image_block, text_block]
    else:
        message_content = [text_block]
    # 2. Создаём сообщение в thread
    try:
        await asyncio.wait_for(
            asyncio.to_thread(
                client.beta.threads.messages.create,
                thread_id=thread_id,
                role="user",
                content=message_content,
            ),
            timeout=MESSAGE_CREATION_TIMEOUT,
        )
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create message: %s", exc)
        raise
    except asyncio.TimeoutError:
        message = "Message creation timed out"
        logger.exception("[OpenAI] %s", message)
        raise RuntimeError(message)

    # 3. Запускаем ассистента
    try:
        run = await asyncio.wait_for(
            asyncio.to_thread(
                client.beta.threads.runs.create,
                thread_id=thread_id,
                assistant_id=settings.openai_assistant_id,
            ),
            timeout=RUN_CREATION_TIMEOUT,
        )
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create run: %s", exc)
        raise
    except asyncio.TimeoutError:
        message = "Run creation timed out"
        logger.exception("[OpenAI] %s", message)
        raise RuntimeError(message)

    if run is None:
        message = "Run creation returned None"
        logger.error("[OpenAI] %s", message)
        raise RuntimeError(message)
    else:
        logger.debug("[OpenAI] Run %s started (thread %s)", run.id, thread_id)
        return run
