# gpt_client.py

import logging
import os
import threading

from openai import OpenAIError

from diabetes.config import OPENAI_ASSISTANT_ID
from diabetes.openai_utils import get_openai_client

logger = logging.getLogger(__name__)

_client = None
_client_lock = threading.Lock()


def _get_client():
    global _client
    if _client is None:
        with _client_lock:
            if _client is None:
                _client = get_openai_client()
    return _client


def create_thread() -> str:
    """Создаём пустой thread (ассистент задаётся позже, в runs.create)."""
    try:
        thread = _get_client().beta.threads.create()
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create thread: %s", exc)
        raise
    return thread.id


def send_message(
    thread_id: str,
    content: str | None = None,
    image_path: str | None = None,
    *,
    keep_image: bool = False,
):
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
    text_block = {
        "type": "text",
        "text": content if content is not None else "Что изображено на фото?",
    }
    if image_path:
        try:
            with open(image_path, "rb") as f:
                file = _get_client().files.create(file=f, purpose="vision")
        except OSError as exc:
            logger.exception("[OpenAI] Failed to read %s: %s", image_path, exc)
            raise
        except OpenAIError as exc:
            logger.exception("[OpenAI] Failed to upload %s: %s", image_path, exc)
            raise
        else:
            logger.info(
                "[OpenAI] Uploaded image %s, file_id=%s", image_path, file.id
            )
            content_block = [
                {"type": "image_file", "image_file": {"file_id": file.id}},
                text_block,
            ]
            if not keep_image:
                try:
                    os.remove(image_path)
                except OSError as e:
                    logger.warning(
                        "[OpenAI] Failed to delete %s: %s", image_path, e
                    )
    else:
        content_block = [text_block]

    # 2. Создаём сообщение в thread
    try:
        _get_client().beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content_block,
        )
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create message: %s", exc)
        raise

    # 3. Запускаем ассистента
    try:
        run = _get_client().beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=OPENAI_ASSISTANT_ID,
        )
    except OpenAIError as exc:
        logger.exception("[OpenAI] Failed to create run: %s", exc)
        raise
    logger.debug("[OpenAI] Run %s started (thread %s)", run.id, thread_id)
    return run
