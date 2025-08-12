from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Reminder")


@_attrs_define
class Reminder:
    """
    Attributes:
        telegram_id (int):
        type_ (str):
        id (Union[Unset, int]):
        time (Union[Unset, str]):
        interval_hours (Union[None, Unset, int]):
        is_enabled (Union[Unset, bool]):
    """

    telegram_id: int
    type_: str
    id: Union[Unset, int] = UNSET
    time: Union[Unset, str] = UNSET
    interval_hours: Union[None, Unset, int] = UNSET
    is_enabled: Union[Unset, bool] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        telegram_id = self.telegram_id

        type_ = self.type_

        id = self.id

        time = self.time

        interval_hours: Union[None, Unset, int]
        if isinstance(self.interval_hours, Unset):
            interval_hours = UNSET
        else:
            interval_hours = self.interval_hours

        is_enabled = self.is_enabled

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "telegram_id": telegram_id,
                "type": type_,
            }
        )
        if id is not UNSET:
            field_dict["id"] = id
        if time is not UNSET:
            field_dict["time"] = time
        if interval_hours is not UNSET:
            field_dict["interval_hours"] = interval_hours
        if is_enabled is not UNSET:
            field_dict["is_enabled"] = is_enabled

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        telegram_id = d.pop("telegram_id")

        type_ = d.pop("type")

        id = d.pop("id", UNSET)

        time = d.pop("time", UNSET)

        def _parse_interval_hours(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        interval_hours = _parse_interval_hours(d.pop("interval_hours", UNSET))

        is_enabled = d.pop("is_enabled", UNSET)

        reminder = cls(
            telegram_id=telegram_id,
            type_=type_,
            id=id,
            time=time,
            interval_hours=interval_hours,
            is_enabled=is_enabled,
        )

        reminder.additional_properties = d
        return reminder

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
