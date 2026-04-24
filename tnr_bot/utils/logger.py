import asyncio
import logging
import sys
from typing import Optional


class TelegramChatHandler(logging.StreamHandler):
    def __init__(
        self,
        app,
        chat_id: int,
        app_name: str,
        ping_developers: Optional[str],
        loop: asyncio.AbstractEventLoop,
        level: int = logging.NOTSET,
        stream=sys.stdout
    ):
        super().__init__(stream)

        self.app = app
        self.chat_id = chat_id
        self.loop = loop
        self.min_level = level
        self.app_name = app_name
        self.ping_developers = ping_developers

    async def send_message(self, message: str):
        try:
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
        except Exception as e:
            print(e)

    def emit(self, record: logging.LogRecord):
        try:
            if record.levelno < self.min_level:
                return

            msg = self.app_name + '| ' + self.format(record)

            if record.levelno >= logging.ERROR and self.ping_developers:
                msg = self.ping_developers + ' ' + msg

            asyncio.run_coroutine_threadsafe(
                self.send_message(msg),
                self.loop
            )

        except Exception:
            self.handleError(record)


def setup_logging(app, chat_id, app_name, ping_developers, loop):
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)

    format = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(format)
    root.addHandler(console)

    if chat_id:
        tg_chat_handler = TelegramChatHandler(app, chat_id, app_name, ping_developers, loop, level=logging.WARNING)
        tg_chat_handler.setFormatter(format)
        root.addHandler(tg_chat_handler)
    else:
        root.warning("No chat id for logging provided")