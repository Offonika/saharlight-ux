"""Prometheus metrics for the learning subsystem."""

from __future__ import annotations

from prometheus_client import Counter, Summary

lessons_started: Counter = Counter(
    "lessons_started", "Total number of lessons started"
)
lessons_completed: Counter = Counter(
    "lessons_completed", "Total number of lessons completed"
)
quiz_avg_score: Summary = Summary(
    "quiz_avg_score", "Average quiz score across completed lessons"
)

lesson_log_failures: Counter = Counter(
    "lesson_log_failures", "Total number of lesson log write failures"
)
