from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LearningProfileSchema(BaseModel):
    age_group: str | None = None
    learning_level: str | None = None
    diabetes_type: str | None = None

    model_config = ConfigDict(from_attributes=True)
