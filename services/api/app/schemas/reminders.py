from pydantic import BaseModel


class ReminderSchema(BaseModel):
    telegram_id: int
    id: int | None = None
    type: str
    time: str | None = None
    interval_hours: int | None = None
    minutes_after: int | None = None
    is_enabled: bool = True
