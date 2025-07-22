import pytest
from services import find_protocol_by_diagnosis


def test_find_protocol_found():
    assert find_protocol_by_diagnosis("Диабет 2 типа") == "standard protocol"


def test_find_protocol_not_found():
    assert find_protocol_by_diagnosis("Неизвестный диагноз") is None


