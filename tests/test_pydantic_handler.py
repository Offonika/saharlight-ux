import json

import pytest
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from services.api.app import main


class DummyModel(BaseModel):
    num: int


@pytest.mark.asyncio
async def test_pydantic_422_handler_returns_readable_errors() -> None:
    with pytest.raises(ValidationError) as exc:
        DummyModel(num="bad")

    response = await main.pydantic_422(Request({"type": "http"}), exc.value)
    assert response.status_code == 422
    detail = json.loads(response.body.decode())
    assert detail["detail"][0]["msg"]
