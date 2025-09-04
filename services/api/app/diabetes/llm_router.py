"""Utilities for choosing LLM models for learning tasks."""

from __future__ import annotations

from enum import Enum

from services.api.app import config


class LLMTask(str, Enum):
    """Supported learning tasks routed to different LLM models."""

    EXPLAIN_STEP = "explain_step"
    QUIZ_CHECK = "quiz_check"
    LONG_PLAN = "long_plan"


class LLMRouter:
    """Select the model to use for a given :class:`LLMTask`."""

    def __init__(self, default_model: str | None = None) -> None:
        self._default_model = (
            default_model
            if default_model is not None
            else config.get_settings().learning_model_default
        )

    def choose_model(self, task: LLMTask) -> str:
        """Return the model name appropriate for *task*.

        Currently all tasks use the default model, but the router centralizes
        the decision to simplify future improvements.
        """

        return self._default_model


__all__ = ["LLMRouter", "LLMTask"]
