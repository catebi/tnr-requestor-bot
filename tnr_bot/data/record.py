import hashlib
import json
from typing import List

from pydantic import BaseModel


class RecordStatus: # It would be cool to use Enums and datetime fields in future instead of plain str from Airtable
    NEW_RECORD = 0
    APPLICANT_COMMUNICATION = 1
    STERILIZATION_SCHEDULED = 2
    STERILIZATION_POSTPONED = 3
    TRANSFERRING_TO_SHELTER = 4
    COMPLETED = 5
    STERILIZATION_CANCELED = 6
    ACCEPTED_IN_SHELTER = 7
    APPLICANT_COMMUNICATION_STOPPED = 8



class Record(BaseModel):
    record_id: str
    created_date: str
    status: str
    operator: List[str]

    @property
    def fingerprint(self) -> str:
        payload = {
            "id": self.record_id,
            "created": self.created_date,
            "status": self.status,
            "operator": self.operator,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()
