"""Utilities for building learning-mode prompts.

This module centralizes all prompt text for the learning features of the
bot.  Every prompt includes a standard disclaimer reminding users that the
assistant does not provide medical advice.
"""

from __future__ import annotations

from openai.types.chat import ChatCompletionMessageParam

# The warning is kept in a constant so the text is identical everywhere.
_STANDARD_DISCLAIMER: str = (
    "\u26a0\ufe0f This information is for educational purposes only and "
    "is not a substitute for professional medical advice. Always consult "
    "your healthcare provider."
)


def disclaimer() -> str:
    """Return the standard warning for learning prompts."""

    return _STANDARD_DISCLAIMER


def explain_step_prompt(step: str) -> list[ChatCompletionMessageParam]:
    """Build a prompt asking the model to explain a lesson step."""

    return [
        {"role": "system", "content": disclaimer()},
        {"role": "user", "content": step},
    ]


def quiz_check_prompt(
    question: str, options: list[str], answer_index: int
) -> list[ChatCompletionMessageParam]:
    """Build a prompt asking the model to verify a quiz answer."""

    options_text = ", ".join(options)
    user_text = f"Question: {question}\nOptions: {options_text}\nUser answer index: {answer_index}"
    return [
        {"role": "system", "content": disclaimer()},
        {"role": "user", "content": user_text},
    ]


def long_plan_prompt(goal: str) -> list[ChatCompletionMessageParam]:
    """Build a prompt asking the model to draft a long-term plan."""

    return [
        {"role": "system", "content": disclaimer()},
        {"role": "user", "content": goal},
    ]


__all__ = [
    "disclaimer",
    "explain_step_prompt",
    "quiz_check_prompt",
    "long_plan_prompt",
]
