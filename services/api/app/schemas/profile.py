from datetime import time

from pydantic import BaseModel, Field


class ProfileSchema(BaseModel):
    telegram_id: int
    icr: float
    cf: float
    target: float
    low: float
    high: float
    org_id: int | None = None
    quiet_start: time | None = Field(default=None, alias="quietStart")
    quiet_end: time | None = Field(default=None, alias="quietEnd")

    class Config:
        allow_population_by_field_name = True
