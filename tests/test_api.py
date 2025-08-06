import pytest

from api import ai_diagnose, DiagnoseRequest

@pytest.mark.asyncio
async def test_ai_diagnose_with_protocol():
    result = await ai_diagnose(DiagnoseRequest(diagnosis="диабет 2 типа"))
    assert result.protocol == "standard protocol"

@pytest.mark.asyncio
async def test_ai_diagnose_without_protocol():
    result = await ai_diagnose(DiagnoseRequest(diagnosis="unknown"))
    assert result.protocol is None

