from __future__ import annotations

from typing import Any, Optional, Sequence
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .services.db import Base, User


class LearningPlan(Base):
    __tablename__ = "learning_plans"
    __table_args__ = (sa.Index("ix_learning_plans_user_id_is_active", "user_id", "is_active"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa.true())
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    plan_json: Mapped[dict[str, Any]] = mapped_column(sa.JSON().with_variant(JSONB, "postgresql"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), onupdate=sa.func.now())

    user: Mapped[User] = relationship("User")
    progresses: Mapped[list["LearningProgress"]] = relationship(
        "LearningProgress", back_populates="plan", cascade="all, delete-orphan"
    )


class LearningProgress(Base):
    __tablename__ = "learning_progress"
    __table_args__ = (
        sa.Index("ix_learning_progress_user_id_plan_id", "user_id", "plan_id"),
        sa.Index("ix_learning_progress_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False)
    plan_id: Mapped[int] = mapped_column(ForeignKey("learning_plans.id"), nullable=False)
    progress_json: Mapped[dict[str, Any]] = mapped_column(
        sa.JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=sa.func.now(),
        onupdate=sa.func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship("User")
    plan: Mapped["LearningPlan"] = relationship("LearningPlan", back_populates="progresses")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=sa.true())

    steps: Mapped[list["LessonStep"]] = relationship(
        "LessonStep",
        back_populates="lesson",
        cascade="all, delete-orphan",
        order_by="LessonStep.step_order",
    )

    questions: Mapped[list["QuizQuestion"]] = relationship(
        "QuizQuestion", back_populates="lesson", cascade="all, delete-orphan"
    )
    progresses: Mapped[list["LessonProgress"]] = relationship(
        "LessonProgress", back_populates="lesson", cascade="all, delete-orphan"
    )


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Sequence[str]] = mapped_column(sa.JSON().with_variant(JSONB, "postgresql"), nullable=False)
    correct_option: Mapped[int] = mapped_column(Integer, nullable=False)

    lesson: Mapped[Lesson] = relationship("Lesson", back_populates="questions")


class LessonStep(Base):
    __tablename__ = "lesson_steps"
    __table_args__ = (sa.UniqueConstraint("lesson_id", "step_order", name="lesson_steps_lesson_order_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    lesson: Mapped[Lesson] = relationship("Lesson", back_populates="steps")


class LessonProgress(Base):
    __tablename__ = "lesson_progress"
    __table_args__ = (sa.UniqueConstraint("user_id", "lesson_id", name="lesson_progress_user_lesson_key"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    lesson_id: Mapped[int] = mapped_column(ForeignKey("lessons.id"), nullable=False, index=True)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_question: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    quiz_score: Mapped[Optional[int]] = mapped_column(Integer)

    user: Mapped[User] = relationship("User")
    lesson: Mapped[Lesson] = relationship("Lesson", back_populates="progresses")


class LessonLog(Base):
    __tablename__ = "lesson_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id"), nullable=False, index=True)
    topic_slug: Mapped[str] = mapped_column(String, nullable=False, index=True)
    role: Mapped[str] = mapped_column(String, nullable=False)
    step_idx: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False)

    user: Mapped[User] = relationship("User")
