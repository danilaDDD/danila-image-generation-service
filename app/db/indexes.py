from pymongo import IndexModel
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.database import Database

# Аналог alembic-миграций для Mongo: create_indexes идемпотентен,
# поэтому вызывается на каждом старте приложения.
# Ключ — имя коллекции, значение — её индексы, например:
#     "scenes": [IndexModel([("user_id", ASCENDING)], name = "ix_user_id")],
COLLECTION_INDEXES: dict[str, list[IndexModel]] = {}


# Возвращает имена применённых индексов: вызывающему коду (scripts/migrate.py) есть
# что показать в выводе, а lifespan результат просто игнорирует.
async def ensure_indexes(database: AsyncDatabase) -> list[str]:
    index_names = []
    for collection_name, indexes in COLLECTION_INDEXES.items():
        index_names += await database[collection_name].create_indexes(indexes)

    return index_names


# Синхронный близнец для тех, кто живёт вне FastAPI: скрипт миграции и Celery-воркер.
def ensure_indexes_sync(database: Database) -> list[str]:
    index_names = []
    for collection_name, indexes in COLLECTION_INDEXES.items():
        index_names += database[collection_name].create_indexes(indexes)

    return index_names
