"""OpenAI client wrapper with lazy initialization.

This module exposes :class:`OpenAIClient` which encapsulates thread-safe
initialization of the underlying OpenAI client and provides helper methods for
creating threads and sending messages to the Assistant API.
"""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Any

from openai import OpenAIError

from services.api.app.config import settings
from services.api.app.diabetes.utils.openai_utils import get_openai_client


logger = logging.getLogger(__name__)


class OpenAIClient:
    """A thin wrapper around the OpenAI SDK used in the project.

    The underlying client is created lazily and shared between threads.  Methods
    in this class mirror the previous module-level helper functions so existing
    call sites can simply instantiate :class:`OpenAIClient` and use the methods
    ``create_thread`` and ``send_message``.
    """

    def __init__(self) -> None:
        self._client: Any | None = None
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Client management
    # ------------------------------------------------------------------
    def _get_client(self) -> Any:
        """Return a cached OpenAI client instance creating it if necessary."""

        if self._client is None:
            with self._lock:
                if self._client is None:
                    self._client = get_openai_client()
        return self._client

    @property
    def client(self) -> Any:
        """Expose the underlying OpenAI client (read‑only)."""

        return self._get_client()

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------
    def create_thread(self) -> str:
        """Создаём пустой thread (ассистент задаётся позже, в runs.create)."""

        try:
            thread = self._get_client().beta.threads.create()
        except OpenAIError as exc:  # pragma: no cover - network errors
            logger.exception("[OpenAI] Failed to create thread: %s", exc)
            raise
        return thread.id

    async def send_message(
        self,
        *,
        thread_id: str,
        content: str | None = None,
        image_path: str | None = None,
        keep_image: bool = False,
    ):
        """Send text or (image + text) to the thread and start a run.

        Parameters
        ----------
        thread_id: str
            Target thread identifier.
        content: str | None
            Text message to send.  Must be provided if ``image_path`` is
            ``None``.
        image_path: str | None
            Path to an image to upload alongside the text.
        keep_image: bool, default ``False``
            If ``True`` the local file will not be removed after attempting the
            upload.

        Returns
        -------
        run
            The created run object.
        """

        if content is None and image_path is None:
            raise ValueError("Either 'content' or 'image_path' must be provided")

        client = self._get_client()
        text_block = {
            "type": "text",
            "text": content if content is not None else "Что изображено на фото?",
        }

        if image_path:
            try:
                def _upload() -> Any:
                    with open(image_path, "rb") as f:
                        return client.files.create(file=f, purpose="vision")

                file = await asyncio.to_thread(_upload)
            except OSError as exc:
                logger.exception("[OpenAI] Failed to read %s: %s", image_path, exc)
                raise
            except OpenAIError as exc:  # pragma: no cover - network errors
                logger.exception(
                    "[OpenAI] Failed to upload %s: %s", image_path, exc
                )
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
                        await asyncio.to_thread(os.remove, image_path)
                    except OSError as e:  # pragma: no cover - best effort
                        logger.warning(
                            "[OpenAI] Failed to delete %s: %s", image_path, e
                        )
        else:
            content_block = [text_block]

        try:
            await asyncio.to_thread(
                client.beta.threads.messages.create,
                thread_id=thread_id,
                role="user",
                content=content_block,
            )
        except OpenAIError as exc:  # pragma: no cover - network errors
            logger.exception("[OpenAI] Failed to create message: %s", exc)
            raise

        if not settings.openai_assistant_id:
            message = "OPENAI_ASSISTANT_ID is not set"
            logger.error("[OpenAI] %s", message)
            raise RuntimeError(message)

        try:
            run = await asyncio.to_thread(
                client.beta.threads.runs.create,
                thread_id=thread_id,
                assistant_id=settings.openai_assistant_id,
            )
        except OpenAIError as exc:  # pragma: no cover - network errors
            logger.exception("[OpenAI] Failed to create run: %s", exc)
            raise

        logger.debug("[OpenAI] Run %s started (thread %s)", run.id, thread_id)
        return run

