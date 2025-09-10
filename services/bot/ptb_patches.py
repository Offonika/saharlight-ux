# file: services/bot/ptb_patches.py
"""
Небольшой воркараунд для PTB 21.1.x:
- Чиним AttributeError в JobQueue.stop() на AsyncIOExecutor (_pending_futures).
- Если оригинальный stop упал — мягко гасим APScheduler без ожидания.
"""

from __future__ import annotations

import logging
from typing import Any


logger = logging.getLogger(__name__)

def apply_jobqueue_stop_workaround() -> None:
    try:
        # Импортируем внутренности PTB — да, это «приватный» модуль.
        import telegram.ext._jobqueue as jq_mod  # type: ignore[attr-defined]
    except ImportError:
        logger.warning("telegram.ext._jobqueue not found; JobQueue stop workaround not applied", exc_info=True)
        return

    if getattr(jq_mod.JobQueue.stop, "_patched_asyncio_executor_fix", False):  # уже пропатчено
        return

    _orig_stop = jq_mod.JobQueue.stop

    async def _patched_stop(self, wait: bool = True) -> Any:
        try:
            # пробуем штатный путь
            return await _orig_stop(self, wait=wait)  # type: ignore[misc]
        except AttributeError as e:
            # именно тот кейс с AsyncIOExecutor и _pending_futures
            if "_pending_futures" in str(e):
                try:
                    # мягко гасим планировщик; wait=False, чтобы не ловить "Event loop is closed"
                    if hasattr(self, "scheduler") and self.scheduler:
                        self.scheduler.shutdown(wait=False)
                except Exception:
                    logger.exception("Unexpected error while shutting down scheduler")
                return
            raise

    # помечаем, чтобы не патчить дважды
    _patched_stop._patched_asyncio_executor_fix = True  # type: ignore[attr-defined]
    jq_mod.JobQueue.stop = _patched_stop  # type: ignore[assignment]
