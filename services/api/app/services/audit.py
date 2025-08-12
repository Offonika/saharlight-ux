import logging
from typing import Optional

audit_logger = logging.getLogger("audit")


def log_patient_access(user_id: Optional[str], patient_id: int) -> None:
    audit_logger.info("user=%s accessed patient=%s", user_id, patient_id)
