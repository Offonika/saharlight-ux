"""Prometheus metrics for learning lessons."""

from prometheus_client import Counter, Summary

lessons_started = Counter(
    "lessons_started",
    "Number of lessons started by users",
)
lessons_completed = Counter(
    "lessons_completed",
    "Number of lessons successfully completed",
)
quiz_avg_score = Summary(
    "quiz_avg_score",
    "Average quiz score percentage upon lesson completion",
)

__all__ = ["lessons_started", "lessons_completed", "quiz_avg_score"]
