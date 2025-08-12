from collections.abc import Mapping
from typing import Any, TypeVar, Union, cast

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

T = TypeVar("T", bound="Profile")


@_attrs_define
class Profile:
    """
    Attributes:
        telegram_id (int):
        icr (float):
        cf (float):
        target (float):
        low (float):
        high (float):
        org_id (Union[None, Unset, int]):
    """

    telegram_id: int
    icr: float
    cf: float
    target: float
    low: float
    high: float
    org_id: Union[None, Unset, int] = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)

    def to_dict(self) -> dict[str, Any]:
        telegram_id = self.telegram_id

        icr = self.icr

        cf = self.cf

        target = self.target

        low = self.low

        high = self.high

        org_id: Union[None, Unset, int]
        if isinstance(self.org_id, Unset):
            org_id = UNSET
        else:
            org_id = self.org_id

        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update(
            {
                "telegram_id": telegram_id,
                "icr": icr,
                "cf": cf,
                "target": target,
                "low": low,
                "high": high,
            }
        )
        if org_id is not UNSET:
            field_dict["org_id"] = org_id

        return field_dict

    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        telegram_id = d.pop("telegram_id")

        icr = d.pop("icr")

        cf = d.pop("cf")

        target = d.pop("target")

        low = d.pop("low")

        high = d.pop("high")

        def _parse_org_id(data: object) -> Union[None, Unset, int]:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(Union[None, Unset, int], data)

        org_id = _parse_org_id(d.pop("org_id", UNSET))

        profile = cls(
            telegram_id=telegram_id,
            icr=icr,
            cf=cf,
            target=target,
            low=low,
            high=high,
            org_id=org_id,
        )

        profile.additional_properties = d
        return profile

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
