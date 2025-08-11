from pydantic import BaseModel


class TimezoneSchema(BaseModel):
    telegram_id: int
    tz: str


class ProfileSchema(BaseModel):
    telegram_id: int
    icr: float
    cf: float
    target: float
    low: float
    high: float


class ReminderSchema(BaseModel):
    telegram_id: int
    id: int | None = None
    type: str
    time: str | None = None
    interval_hours: int | None = None
    minutes_after: int | None = None
    is_enabled: bool = True
