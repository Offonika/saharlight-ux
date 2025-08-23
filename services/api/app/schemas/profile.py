from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class ProfileSchema(BaseModel):
    telegramId: int = Field(alias="telegramId", validation_alias=AliasChoices("telegramId", "telegram_id"))
    icr: float
    cf: float
    target: float
    low: float
    high: float
    orgId: int | None = None
    sosContact: str | None = Field(
        default=None,
        alias="sosContact",
        validation_alias=AliasChoices("sosContact", "sos_contact"),
    )
    sosAlertsEnabled: bool | None = Field(
        default=None,
        alias="sosAlertsEnabled",
        validation_alias=AliasChoices("sosAlertsEnabled", "sos_alerts_enabled"),
    )

    model_config = ConfigDict(populate_by_name=True)
