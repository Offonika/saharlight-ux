from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ReminderSchema(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))
    id: int | None = None
    type: str
    time: str | None = None
    intervalHours: int | None = None
    minutesAfter: int | None = None
    isEnabled: bool = True
    orgId: int | None = None

    model_config = ConfigDict(populate_by_name=True)
