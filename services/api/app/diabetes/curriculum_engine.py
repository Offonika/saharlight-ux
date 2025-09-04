from __future__ import annotations

from collections import defaultdict
from typing import Any


from .learning_prompts import build_explain_step, build_quiz_check
from .llm_router import LLMTask
from .models_learning import LessonProgress, LessonStep, QuizQuestion
from .services import db, gpt_client

_state: dict[int, dict[str, Any]] = defaultdict(dict)


async def _ask_llm(task: LLMTask, content: str) -> str:
    completion = await gpt_client.create_learning_chat_completion(
        task=task, messages=[{"role": "user", "content": content}]
    )
    return completion.choices[0].message.content or ""


async def start_lesson(user_id: int, lesson_id: int) -> str:
    with db.SessionLocal() as session:
        steps = (
            session.query(LessonStep)
            .filter_by(lesson_id=lesson_id)
            .order_by(LessonStep.step_order)
            .all()
        )
    if not steps:
        raise ValueError("no steps")
    _state[user_id] = {
        "lesson_id": lesson_id,
        "steps": [s.content for s in steps],
        "step_idx": 0,
        "quiz_idx": 0,
        "score": 0,
    }
    prompt = build_explain_step(steps[0].content)
    return await _ask_llm(LLMTask.EXPLAIN_STEP, prompt)


async def next_step(user_id: int) -> str:
    data = _state[user_id]
    data["step_idx"] += 1
    steps: list[str] = data["steps"]
    idx = data["step_idx"]
    if idx < len(steps):
        prompt = build_explain_step(steps[idx])
        return await _ask_llm(LLMTask.EXPLAIN_STEP, prompt)
    return "Quiz time"


async def check_answer(user_id: int, answer: int) -> str:
    data = _state[user_id]
    lesson_id = data["lesson_id"]
    with db.SessionLocal() as session:
        questions = (
            session.query(QuizQuestion)
            .filter_by(lesson_id=lesson_id)
            .order_by(QuizQuestion.id)
            .all()
        )
    question = questions[data["quiz_idx"]]
    correct = question.correct_option == answer
    prompt = build_quiz_check(question.question, question.options)
    data["quiz_idx"] += 1
    if correct:
        data["score"] += 1
    feedback = await _ask_llm(LLMTask.QUIZ_CHECK, prompt)
    if data["quiz_idx"] >= len(questions):
        score = int(100 * data["score"] / len(questions))
        with db.SessionLocal() as session:
            session.add(
                LessonProgress(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    completed=True,
                    quiz_score=score,
                )
            )
            session.commit()
    return feedback


__all__ = ["start_lesson", "next_step", "check_answer"]
