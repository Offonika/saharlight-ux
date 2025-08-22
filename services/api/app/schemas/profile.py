from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProfileSchema(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))
    icr: float
    cf: float
    target: float
    low: float
    high: float
    orgId: int | None = None

    model_config = ConfigDict(populate_by_name=True)
