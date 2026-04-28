from datetime import datetime
from typing import Optional

from apscheduler.job import Job
from pydantic import BaseModel

from tnr_bot.data.record import Record


class RecordHistory(BaseModel):
    scheduled_time: Optional[datetime]
    scheduled_job: Optional[Job]
    last_sent_message_data: Optional[Record]
    fail_count: int = 0

    class Config:
        arbitrary_types_allowed = True
        allow_mutation = True

