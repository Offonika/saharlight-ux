from __future__ import annotations

from typing import TypeAlias
from telegram.ext import ContextTypes, Job as PTBJob, JobQueue as PTBJobQueue

JobQueue: TypeAlias = PTBJobQueue[ContextTypes.DEFAULT_TYPE]
Job: TypeAlias = PTBJob[ContextTypes.DEFAULT_TYPE]

__all__ = ["JobQueue", "Job"]
