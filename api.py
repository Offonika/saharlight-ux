from fastapi import FastAPI
from pydantic import BaseModel
from services import find_protocol_by_diagnosis

app = FastAPI()

class DiagnoseRequest(BaseModel):
    diagnosis: str

class DiagnoseResponse(BaseModel):
    protocol: str | None

@app.post("/v1/ai/diagnose", response_model=DiagnoseResponse)
async def ai_diagnose(req: DiagnoseRequest):
    protocol = find_protocol_by_diagnosis(req.diagnosis)
    return {"protocol": protocol}

