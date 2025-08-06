PROTOCOLS = {
    "диабет 2 типа": "standard protocol",
    "диабет 1 типа": "insulin protocol",
}


def find_protocol_by_diagnosis(diagnosis: str | None) -> str | None:
    if not diagnosis:
        return None
    diagnosis = diagnosis.strip().lower()
    return PROTOCOLS.get(diagnosis)

