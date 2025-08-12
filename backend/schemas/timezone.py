from pydantic import BaseModel


class TimezoneSchema(BaseModel):
    telegram_id: int
    tz: str
