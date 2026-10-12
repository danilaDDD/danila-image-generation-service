from contextlib import asynccontextmanager, contextmanager
from functools import wraps
from typing import Any, AsyncGenerator, Callable, Generator, TypeVar, cast

from fastapi import Depends
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.database import Database

from app.db.connection import get_async_database_factory

RepositoryT = TypeVar("RepositoryT")


def repository(getter: Callable[[Any], RepositoryT]) -> RepositoryT:

    @wraps(getter)
    def wrapper(self: Any) -> RepositoryT:
        if self._database is None:
            raise RuntimeError(
                f"Репозиторий '{getter.__name__}' доступен только внутри start(): "
                "вне контекста база не выбрана."
            )

        return getter(self)

    # Снаружи атрибут читается как сам репозиторий, поэтому property
    # прикидывается его типом — иначе mypy видит на месте обращения property.
    return cast(RepositoryT, property(wrapper))


class AsyncSessionManager:
    def __init__(self, database_factory: Callable[[], AsyncDatabase]):
        self._database_factory = database_factory
        self._database = None

    def get_database(self) -> AsyncDatabase | None:
        return self._database

    def get_database_factory(self) -> Callable[[], AsyncDatabase]:
        return self._database_factory

    def _acquire_database(self) -> None:
        # Экземпляр держит выбранную базу в поле, поэтому вложенное или
        # параллельное использование одного менеджера затирает состояние:
        # выход из внутреннего контекста обнуляет поле у ещё открытого внешнего.
        # Ловим это сразу и громко вместо молчаливой порчи.
        if self._database is not None:
            raise RuntimeError(
                "AsyncSessionManager уже активен. Вложенное или параллельное "
                "использование одного экземпляра затрёт его состояние — "
                "создайте отдельный менеджер на каждую единицу работы."
            )

        self._database = self._database_factory()

    def _release_database(self) -> None:
        self._database = None

    # В Mongo коммитить нечего: все записи однодокументные и атомарны сами по себе.
    # Сессия pymongo (ClientSession) здесь тоже не открывается — менеджер только
    # выбирает базу, поэтому контекст ровно один.
    @asynccontextmanager
    async def start(self) -> AsyncGenerator["AsyncSessionManager", Any]:
        self._acquire_database()
        try:
            yield self
        finally:
            self._release_database()

    # Репозитории объявляются здесь через @repository, например:
    #     @repository
    #     def scenes(self) -> AsyncSceneRepository:
    #         return AsyncSceneRepository(self._database)


class SyncSessionManager:
    def __init__(self, database_factory: Callable[[], Database]):
        self._database_factory = database_factory
        self._database = None

    def get_database(self) -> Database | None:
        return self._database

    def get_database_factory(self) -> Callable[[], Database]:
        return self._database_factory

    def _acquire_database(self) -> None:
        # То же, что и в AsyncSessionManager: экземпляр stateful, поэтому
        # повторный вход без выхода — ошибка, а не тихая перезапись. Для
        # Celery это важнее всего: объект BaseTask переиспользуется между
        # задачами, и менеджер там живёт дольше одной задачи.
        if self._database is not None:
            raise RuntimeError(
                "SyncSessionManager уже активен. Вложенное или параллельное "
                "использование одного экземпляра затрёт его состояние — "
                "создайте отдельный менеджер на каждую единицу работы."
            )

        self._database = self._database_factory()

    def _release_database(self) -> None:
        self._database = None

    # В Mongo коммитить нечего: все записи однодокументные и атомарны сами по себе.
    # Сессия pymongo (ClientSession) здесь тоже не открывается — менеджер только
    # выбирает базу, поэтому контекст ровно один.
    @contextmanager
    def start(self) -> Generator["SyncSessionManager", Any, None]:
        self._acquire_database()
        try:
            yield self
        finally:
            self._release_database()

    # Репозитории объявляются здесь через @repository — так же, как в AsyncSessionManager.


def get_async_session_manager(
        database_factory: Callable[[], AsyncDatabase] = Depends(
            get_async_database_factory, use_cache = True)) -> AsyncSessionManager:
    return AsyncSessionManager(database_factory)
