from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LearningProfileSchema(BaseModel):
    age_group: str | None = None
    learning_level: str | None = None
    diabetes_type: str | None = Field(
        default=None, json_schema_extra={"readOnly": True}
    )

    model_config = ConfigDict(from_attributes=True)
