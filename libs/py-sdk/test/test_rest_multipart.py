import json
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


def test_multipart_dict() -> None:
    client = _client()
    mock = MagicMock(return_value=_mock_response())
    client.pool_manager.request = mock  # type: ignore[method-assign]
    client.request(  # type: ignore[no-untyped-call]
        "POST",
        "http://example.com",
        headers={"Content-Type": "multipart/form-data"},
        post_params={"foo": "bar", "baz": {"a": 1}},
    )
    kwargs = mock.call_args.kwargs
    assert kwargs["encode_multipart"] is True
    assert all(len(item) == 2 for item in kwargs["fields"])
    assert kwargs["fields"] == [
        ("foo", "bar"),
        ("baz", json.dumps({"a": 1})),
    ]


def test_multipart_list() -> None:
    client = _client()
    mock = MagicMock(return_value=_mock_response())
    client.pool_manager.request = mock  # type: ignore[method-assign]
    client.request(  # type: ignore[no-untyped-call]
        "POST",
        "http://example.com",
        headers={"Content-Type": "multipart/form-data"},
        post_params=[("foo", "bar"), ("baz", {"a": 1})],
    )
    kwargs = mock.call_args.kwargs
    assert kwargs["encode_multipart"] is True
    assert all(len(item) == 2 for item in kwargs["fields"])
    assert kwargs["fields"] == [
        ("foo", "bar"),
        ("baz", json.dumps({"a": 1})),
    ]


def test_multipart_nested_dict() -> None:
    client = _client()
    mock = MagicMock(return_value=_mock_response())
    client.pool_manager.request = mock  # type: ignore[method-assign]
    nested = {"x": {"y": {"z": 2}}}
    client.request(  # type: ignore[no-untyped-call]
        "POST",
        "http://example.com",
        headers={"Content-Type": "multipart/form-data"},
        post_params={"nested": nested},
    )
    kwargs = mock.call_args.kwargs
    assert kwargs["encode_multipart"] is True
    assert all(len(item) == 2 for item in kwargs["fields"])
    assert kwargs["fields"] == [("nested", json.dumps(nested))]


def test_multipart_list_value() -> None:
    client = _client()
    mock = MagicMock(return_value=_mock_response())
    client.pool_manager.request = mock  # type: ignore[method-assign]
    value = [1, 2]
    client.request(  # type: ignore[no-untyped-call]
        "POST",
        "http://example.com",
        headers={"Content-Type": "multipart/form-data"},
        post_params={"list": value},
    )
    kwargs = mock.call_args.kwargs
    assert kwargs["encode_multipart"] is True
    assert all(len(item) == 2 for item in kwargs["fields"])
    assert kwargs["fields"] == [("list", json.dumps(value))]


def test_multipart_tuple_value() -> None:
    client = _client()
    mock = MagicMock(return_value=_mock_response())
    client.pool_manager.request = mock  # type: ignore[method-assign]
    value = (1, 2)
    client.request(  # type: ignore[no-untyped-call]
        "POST",
        "http://example.com",
        headers={"Content-Type": "multipart/form-data"},
        post_params={"tuple": value},
    )
    kwargs = mock.call_args.kwargs
    assert kwargs["encode_multipart"] is True
    assert all(len(item) == 2 for item in kwargs["fields"])
    assert kwargs["fields"] == [("tuple", json.dumps(value))]


def test_multipart_invalid_post_params() -> None:
    client = _client()
    with pytest.raises(ApiValueError):
        client.request(  # type: ignore[no-untyped-call]
            "POST",
            "http://example.com",
            headers={"Content-Type": "multipart/form-data"},
            post_params=[("foo",)],
        )
