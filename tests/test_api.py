from api import ai_diagnose, DiagnoseRequest
import asyncio


def test_ai_diagnose_with_protocol():
    result = asyncio.run(ai_diagnose(DiagnoseRequest(diagnosis="диабет 2 типа")))
    assert result["protocol"] == "standard protocol"


def test_ai_diagnose_without_protocol():
    result = asyncio.run(ai_diagnose(DiagnoseRequest(diagnosis="unknown")))
    assert result["protocol"] is None



