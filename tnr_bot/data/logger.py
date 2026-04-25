import os
from _typeshed import MaybeNone
from asyncio import AbstractEventLoop
from typing import TextIO, Annotated, Optional

import sys
from pydantic import AfterValidator
from pydantic.v1 import BaseModel
from telegram.ext import Application


def negative_chat_id(chat_id: int) -> int:
    if chat_id > 0:
        return -chat_id
    return chat_id

class LoggerCreateData(BaseModel):
    app: Application
    loop: AbstractEventLoop
    logs_chat_id: Annotated[int, AfterValidator(negative_chat_id)] = os.getenv("LOGS_CHAT_ID")
    app_name: str = os.getenv("APP_NAME")
    ping_developers: Optional[str] = os.getenv("DEVELOPERS")
    stream: TextIO | MaybeNone = sys.stdout
    min_level: int



