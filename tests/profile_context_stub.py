from typing import Any

class ContextStub:
    def __init__(self) -> None:
        self._user_data: dict[str, Any] = {}

    @property
    def user_data(self) -> dict[str, Any]:
        return self._user_data
