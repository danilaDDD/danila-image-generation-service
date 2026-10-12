from typing import Callable

from celery import Task
from celery.signals import worker_process_init, worker_process_shutdown
from pymongo import MongoClient
from pymongo.database import Database

from app.db.connection import create_sync_database_factory, create_sync_mongo_client
from app.db.session_manager import SyncSessionManager
from settings.settings import Settings, load_settings


class WorkerDatabase:
    """Клиент Mongo, живущий ровно столько же, сколько процесс воркера.

    У воркера нет lifespan, поэтому владельцем клиента выступают сигналы Celery.
    Клиент открывается по worker_process_init, а не по worker_init: при forking-пуле
    дочерние процессы унаследовали бы сокеты родителя, а pymongo такое наследование
    не переживает.
    """

    def __init__(self):
        self._mongo_client: MongoClient | None = None
        self._database_factory: Callable[[], Database] | None = None

    def open(self, settings: Settings) -> None:
        if self._mongo_client is not None:
            return

        self._mongo_client = create_sync_mongo_client(settings)
        self._database_factory = create_sync_database_factory(self._mongo_client, settings)

    def close(self) -> None:
        if self._mongo_client is None:
            return

        self._mongo_client.close()
        self._mongo_client = None
        self._database_factory = None

    def get_database_factory(self) -> Callable[[], Database]:
        if self._database_factory is None:
            raise RuntimeError(
                "Клиент Mongo для воркера не открыт: в проде его открывает сигнал "
                "worker_process_init, в тестах — фикстура open_worker_database."
            )

        return self._database_factory


worker_database = WorkerDatabase()


class BaseTask(Task):
    @property
    def settings(self) -> Settings:
        return load_settings()

    # Экземпляр задачи Celery переиспользуется между запусками, а SyncSessionManager
    # stateful и запрещает повторный вход, поэтому держать его в поле нельзя:
    # каждое обращение отдаёт новый менеджер — одна единица работы на задачу.
    @property
    def sync_session_manager(self) -> SyncSessionManager:
        return SyncSessionManager(worker_database.get_database_factory())


@worker_process_init.connect
def open_worker_resources(**kwargs) -> None:
    worker_database.open(load_settings())


@worker_process_shutdown.connect
def close_worker_resources(**kwargs) -> None:
    worker_database.close()
