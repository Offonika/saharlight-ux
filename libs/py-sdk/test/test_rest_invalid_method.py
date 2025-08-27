import pytest

from diabetes_sdk.configuration import Configuration
from diabetes_sdk.exceptions import ApiValueError
from diabetes_sdk.rest import RESTClientObject


def test_request_invalid_method() -> None:
    client = RESTClientObject(Configuration())
    with pytest.raises(ApiValueError):
        client.request("TRACE", "http://example.com")  # type: ignore[no-untyped-call]
