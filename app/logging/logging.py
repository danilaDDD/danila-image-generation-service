import sys

from aiologger import Logger
from aiologger.formatters.base import Formatter
from aiologger.handlers.files import AsyncFileHandler
from aiologger.handlers.streams import AsyncStreamHandler
from fastapi import FastAPI


def initialize_logger(app: FastAPI) -> None:
    logger = Logger(name="error_logger")

    # Добавляем консольный handler (полностью асинхронный)
    stream_handler = AsyncStreamHandler(stream=sys.stdout)
    formatter = Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
    stream_handler.formatter = formatter
    logger.add_handler(stream_handler)

    # Добавляем файловый handler (использует threads в фоне)
    error_file_handler = AsyncFileHandler(filename='logs/error.log')
    error_file_handler.formatter = formatter
    logger.add_handler(error_file_handler)

    # Сохраняем логгер в состоянии приложения
    app.state.logger = logger