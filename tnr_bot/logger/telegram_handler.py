import asyncio
import logging

from tnr_bot.data.logger import LoggerCreateData


class TelegramChatHandler(logging.StreamHandler):
    def __init__(self, logger_create_data: LoggerCreateData):
        super().__init__(logger_create_data.stream)

        self.app = logger_create_data.app
        self.loop = logger_create_data.loop
        self.chat_id = logger_create_data.logs_chat_id
        self.app_name = logger_create_data.app_name
        self.ping_developers = logger_create_data.ping_developers
        self.min_level = logger_create_data.min_level
        self.stream = logger_create_data.stream

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