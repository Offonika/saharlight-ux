PROTOCOLS = {
    "диабет 2 типа": "standard protocol",
    "диабет 1 типа": "insulin protocol",
}

def find_protocol_by_diagnosis(diagnosis: str) -> str | None:
    diagnosis = diagnosis.lower()
    return PROTOCOLS.get(diagnosis)

