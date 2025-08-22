from pydantic import BaseModel


class DayStats(BaseModel):
    sugar: float
    breadUnits: float
    insulin: float


class AnalyticsPoint(BaseModel):
    date: str
    sugar: float
