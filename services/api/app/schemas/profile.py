from pydantic import BaseModel


class ProfileSchema(BaseModel):
    telegram_id: int
    icr: float
    cf: float
    target: float
    low: float
    high: float
    org_id: int | None = None
