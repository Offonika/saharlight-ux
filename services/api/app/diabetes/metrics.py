"""Prometheus metrics for the learning subsystem."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Summary
from prometheus_client.metrics import MetricWrapperBase


def get_metric_value(metric: MetricWrapperBase, suffix: str | None = None) -> float:
    """Return current value of *metric* using only public APIs."""
    for metric_family in metric.collect():
        base_name = metric_family.name
        target = f"{base_name}_{suffix}" if suffix else None
        for sample in metric_family.samples:
            name = sample.name
            if target:
                if name == target:
                    return float(sample.value)
            elif name in {base_name, f"{base_name}_total"}:
                return float(sample.value)
    return 0.0


lessons_started: Counter = Counter(
    "lessons_started",
    "Total number of lessons started",
)
lessons_completed: Counter = Counter(
    "lessons_completed",
    "Total number of lessons completed",
)
quiz_avg_score: Summary = Summary(
    "quiz_avg_score",
    "Average quiz score across completed lessons",
)

db_down_seconds: Gauge = Gauge(
    "db_down_seconds",
    "Seconds database has been unreachable",
)
lesson_log_failures: Counter = Counter(
    "lesson_log_failures",
    "Number of failed lesson log flushes",
)
lesson_log_failures_last: Gauge = Gauge(
    "lesson_log_failures_last",
    "Previously observed lesson_log_failures count",
    multiprocess_mode="max",
)

learning_prompt_cache_hit: Counter = Counter(
    "learning_prompt_cache_hit",
    "Number of learning prompt cache hits",
)
learning_prompt_cache_miss: Counter = Counter(
    "learning_prompt_cache_miss",
    "Number of learning prompt cache misses",
)

pending_logs_size: Gauge = Gauge(
    "pending_logs_size",
    "Number of lesson logs pending flush",
)

step_advance_total: Counter = Counter(
    "step_advance_total",
    "Total number of lesson step advances",
)
