import logging

from tnr_bot.data.logger import LoggerCreateData
from tnr_bot.logger.telegram_handler import TelegramChatHandler


def setup_logging(logger_create_data: LoggerCreateData):
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.INFO)

    format = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    console = logging.StreamHandler()
    console.setFormatter(format)
    root.addHandler(console)

    tg_chat_handler = TelegramChatHandler(logger_create_data)
    tg_chat_handler.setFormatter(format)
    root.addHandler(tg_chat_handler)
