from typing import Callable

from fastapi import Request
from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.database import Database

from settings.settings import Settings

# Клиент Mongo — это пул соединений и фоновый мониторинг топологии, а не одно
# соединение, поэтому он создаётся один раз на процесс и живёт столько же, сколько
# сам процесс. Общего кэша клиентов здесь намеренно нет: владельцев в одном
# процессе несколько (lifespan приложения, процесс Celery-воркера, session-scoped
# фикстуры тестов), и с кэшем один владелец закрывает клиент, которым ещё
# пользуется другой — так тестовый прогон падал с InvalidOperation после того, как
# lifespan закрывал общий клиент. Каждый владелец создаёт свой клиент и сам его
# закрывает.


def create_async_mongo_client(settings: Settings) -> AsyncMongoClient:
    return AsyncMongoClient(
        settings.get_mongo_url(),
        uuidRepresentation = "standard",
        tz_aware = True,
        serverSelectionTimeoutMS = 5000,
    )


def create_sync_mongo_client(settings: Settings) -> MongoClient:
    return MongoClient(
        settings.get_mongo_url(),
        uuidRepresentation = "standard",
        tz_aware = True,
        serverSelectionTimeoutMS = 5000,
    )


# Фабрика привязана к переданному клиенту, а не выбирает его сама: владелец клиента
# виден в месте вызова, и подменить его в тестах можно без глобального состояния.
def create_async_database_factory(mongo_client: AsyncMongoClient,
                                  settings: Settings) -> Callable[[], AsyncDatabase]:
    def database_factory() -> AsyncDatabase:
        return mongo_client[settings.MONGO_DB_NAME]

    return database_factory


def create_sync_database_factory(mongo_client: MongoClient,
                                 settings: Settings) -> Callable[[], Database]:
    def database_factory() -> Database:
        return mongo_client[settings.MONGO_DB_NAME]

    return database_factory


# Зависимость только достаёт фабрику, созданную в lifespan, и ничего не создаёт
# сама — поэтому на приложение приходится ровно один клиент.
# Синхронного аналога нет: sync-клиент нужен только Celery-воркеру, а тот живёт вне
# FastAPI и владеет своим клиентом сам (app/tasks/common.py).
def get_async_database_factory(request: Request) -> Callable[[], AsyncDatabase]:
    return request.app.state.async_database_factory