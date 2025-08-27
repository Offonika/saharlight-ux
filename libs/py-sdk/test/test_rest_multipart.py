import json
from collections import OrderedDict
from typing import Any, Iterable, Mapping, cast
from unittest.mock import MagicMock

import pytest
import urllib3

from diabetes_sdk.configuration import Configuration
from diabetes_sdk.exceptions import ApiValueError
from diabetes_sdk.rest import RESTClientObject


def _client() -> RESTClientObject:
    return RESTClientObject(Configuration())


def _mock_response() -> urllib3.HTTPResponse:
    return urllib3.HTTPResponse(body=b"", status=200, headers={})


def _call_fields(post_params: object) -> list[tuple[str, str]]:
    client = _client()
    mock = MagicMock(return_value=_mock_response())
    cast(Any, client.pool_manager).request = mock
    typed_params = cast(
        Mapping[str, object] | Iterable[tuple[str, object]] | None, post_params
    )
    client.request(
        "POST",
        "http://example.com",
        headers={"Content-Type": "multipart/form-data"},
        post_params=typed_params,
    )
    kwargs = cast(dict[str, Any], mock.call_args.kwargs)
    assert kwargs["encode_multipart"] is True
    fields = cast(list[tuple[str, str]], kwargs["fields"])
    assert all(len(item) == 2 for item in fields)
    assert all(isinstance(k, str) and isinstance(v, str) for k, v in fields)
    return fields


def test_multipart_dict() -> None:
    fields = _call_fields({"foo": "bar", "baz": {"a": 1}})
    assert fields == [("foo", "bar"), ("baz", json.dumps({"a": 1}))]


def test_multipart_mapping() -> None:
    params = OrderedDict([("foo", "bar"), ("baz", {"a": 1})])
    fields = _call_fields(params)
    assert fields == [("foo", "bar"), ("baz", json.dumps({"a": 1}))]


def test_multipart_nested_dict() -> None:
    nested = {"x": {"y": {"z": 2}}}
    fields = _call_fields({"nested": nested})
    assert fields == [("nested", json.dumps(nested))]


def test_multipart_list_value() -> None:
    value = [1, 2]
    fields = _call_fields({"list": value})
    assert fields == [("list", json.dumps(value))]


def test_multipart_sequence_pairs() -> None:
    params = [("foo", {"a": 1}), ("list", [1, 2])]
    fields = _call_fields(params)
    assert fields == [
        ("foo", json.dumps({"a": 1})),
        ("list", json.dumps([1, 2])),
    ]


def test_multipart_coerce_to_strings() -> None:
    params = OrderedDict([(1, True), ("num", 2)])
    fields = _call_fields(params)
    assert fields == [("1", "True"), ("num", "2")]


@pytest.mark.parametrize(
    "post_params",
    [
        [("foo",)],
        [("foo", "bar", "baz")],
        [("foo", "bar"), "baz"],
    ],
)
def test_multipart_invalid_post_params(post_params: list[object]) -> None:
    client = _client()
    with pytest.raises(ApiValueError, match="2-item"):
        client.request(
            "POST",
            "http://example.com",
            headers={"Content-Type": "multipart/form-data"},
            post_params=cast(
                Mapping[str, object] | Iterable[tuple[str, object]] | None,
                post_params,
            ),
        )


def test_multipart_invalid_string() -> None:
    client = _client()
    with pytest.raises(ApiValueError):
        client.request(
            "POST",
            "http://example.com",
            headers={"Content-Type": "multipart/form-data"},
            post_params=cast(
                Mapping[str, object] | Iterable[tuple[str, object]] | None,
                "invalid",
            ),
        )


def test_multipart_invalid_bytes() -> None:
    client = _client()
    with pytest.raises(ApiValueError):
        client.request(
            "POST",
            "http://example.com",
            headers={"Content-Type": "multipart/form-data"},
            post_params=cast(
                Mapping[str, object] | Iterable[tuple[str, object]] | None,
                b"invalid",
            ),
        )
