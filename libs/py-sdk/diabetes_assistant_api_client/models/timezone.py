from collections.abc import Mapping
from typing import Any, TypeVar

from attrs import define as _attrs_define
from attrs import field as _attrs_field

T = TypeVar("T", bound="Timezone")


@_attrs_define
class Timezone:
    """
    Attributes:
        telegram_id (int):
        tz (str):
    """

    telegram_id: int
    tz: str
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        telegram_id = self.telegram_id

        tz = self.tz

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "telegram_id": telegram_id,
                "tz": tz,
            }
        )

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        telegram_id = d.pop("telegram_id")

        tz = d.pop("tz")

        timezone = cls(
            telegram_id=telegram_id,
            tz=tz,
        )

        timezone.additional_properties = d
        return timezone

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
