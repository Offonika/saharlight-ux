from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TimezoneSchema(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))
    tz: str

    model_config = ConfigDict(populate_by_name=True)
