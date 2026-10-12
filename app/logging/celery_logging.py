import logging
import os

from celery.signals import after_setup_logger, after_setup_task_logger

from settings.path import BASE_DIR

# Путь абсолютный, а не relative: воркер могут запустить из любой директории,
# а в контейнере logs/ примонтирован именно на BASE_DIR (/app/logs).
CELERY_LOG_DIR = os.path.join(BASE_DIR, "logs")
CELERY_LOG_PATH = os.path.join(CELERY_LOG_DIR, "celery.log")
CELERY_LOG_FORMAT = "%(asctime)s %(processName)s %(name)s %(levelname)s %(message)s"


def _create_error_file_handler() -> logging.FileHandler:
    os.makedirs(CELERY_LOG_DIR, exist_ok = True)

    handler = logging.FileHandler(CELERY_LOG_PATH, encoding = "utf-8")
    # Уровень стоит на handler'е, а не на логгере: логгер celery остаётся на своём
    # INFO и продолжает писать в stdout, в файл же попадают только ошибки.
    handler.setLevel(logging.ERROR)
    handler.setFormatter(logging.Formatter(CELERY_LOG_FORMAT))

    return handler


def _has_error_file_handler(logger: logging.Logger) -> bool:
    return any(
        isinstance(handler, logging.FileHandler)
        and getattr(handler, "baseFilename", None) == CELERY_LOG_PATH
        for handler in logger.handlers
    )


def attach_error_file_handler(logger: logging.Logger) -> None:
    """Добавляет логгеру Celery файловый handler на logs/celery.log.

    Сигналы приходят по одному на каждый настроенный логгер и повторяются при
    рестарте воркера в том же процессе, поэтому handler проверяется на дубль:
    иначе одна ошибка легла бы в файл несколько раз.
    """
    if os.environ.get("ENV", "dev") == "test":
        return

    if _has_error_file_handler(logger):
        return

    logger.addHandler(_create_error_file_handler())


# after_setup_logger отдаёт корневой логгер воркера (Celery перехватывает его при
# worker_hijack_root_logger=True) — через него проходит celery.app.trace, который
# и пишет "Task ... raised unexpected" вместе с трейсбеком упавшей задачи.
@after_setup_logger.connect
def setup_worker_error_logging(logger: logging.Logger, **kwargs) -> None:
    attach_error_file_handler(logger)


# А это логгер celery.task — родитель всех get_task_logger(__name__) внутри задач.
@after_setup_task_logger.connect
def setup_task_error_logging(logger: logging.Logger, **kwargs) -> None:
    attach_error_file_handler(logger)
