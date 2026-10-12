import uuid
from typing import Any, Generic, Sequence, TypeVar

from pymongo import ReturnDocument, UpdateOne
from pymongo.asynchronous.collection import AsyncCollection
from pymongo.asynchronous.database import AsyncDatabase
from pymongo.collection import Collection
from pymongo.database import Database

from app.models.base import AuditedDocument

# Репозитории параметризуются моделью документа: подкласс объявляется как
# BaseAsyncRepository[Scene], и методы возвращают именно эту модель.
ModelT = TypeVar("ModelT", bound = AuditedDocument)


def build_timestamped_update(document: dict[str, Any]) -> list[dict[str, Any]]:
    """Pipeline-обновление, в котором время проставляет сервер Mongo.

    $$NOW доступен только в pipeline-форме update (MongoDB 4.2+), поэтому
    обычный {"$set": ...} здесь не подходит: $currentDate умеет обновлять
    updated_at, но не умеет проставлять created_at только при вставке.

    Значения оборачиваются в $literal: без этого строка вида "$payload"
    в пользовательских данных была бы истолкована как путь к полю документа.
    """
    fields = {key: {"$literal": value} for key, value in document.items()}
    fields["updated_at"] = "$$NOW"
    fields["created_at"] = {"$ifNull": ["$created_at", "$$NOW"]}

    return [{"$set": fields}]


class BaseAsyncRepository(Generic[ModelT]):
    collection_name: str = ""
    model: type[ModelT]

    def __init__(self, database: AsyncDatabase):
        self.database = database

    async def get_by_id(self, document_id: uuid.UUID) -> ModelT | None:
        document = await self.collection.find_one({"_id": document_id})

        return self.to_model(document)

    async def get_by_ids(self, document_ids: Sequence[uuid.UUID]) -> list[ModelT]:
        if not document_ids:
            return []

        return await self.get_list({"_id": {"$in": list(document_ids)}})

    async def get_all(self) -> list[ModelT]:
        cursor = self.collection.find({})

        return [self.model.from_document(document) async for document in cursor]

    async def save(self, obj: ModelT) -> ModelT:
        document = obj.to_document()
        document_id = document.pop("_id")

        saved_document = await self.collection.find_one_and_update(
            {"_id": document_id},
            build_timestamped_update(document),
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )

        return self.model.from_document(saved_document)

    async def save_all(self, objs: Sequence[ModelT]) -> list[ModelT]:
        if not objs:
            return []

        operations = []
        for obj in objs:
            document = obj.to_document()
            document_id = document.pop("_id")
            operations.append(
                UpdateOne({"_id": document_id}, build_timestamped_update(document), upsert=True))

        await self.collection.bulk_write(operations)

        # $in не гарантирует порядок результатов, поэтому раскладываем по id и
        # возвращаем в порядке аргумента: иначе вызывающий код, сопоставляющий
        # результат с входным списком по позиции, молча перепутает документы.
        saved_documents = await self.get_by_ids([obj.id for obj in objs])
        saved_by_id = {saved.id: saved for saved in saved_documents}

        return [saved_by_id[obj.id] for obj in objs]

    @property
    def collection(self) -> AsyncCollection:
        return self.database[self.collection_name]

    async def get_one_or_none(self, query: dict[str, Any]) -> ModelT | None:
        document = await self.collection.find_one(query)

        return self.to_model(document)

    async def get_list(self, query: dict[str, Any]) -> list[ModelT]:
        cursor = self.collection.find(query)

        return [self.model.from_document(document) async for document in cursor]

    def to_model(self, document: dict[str, Any] | None) -> ModelT | None:
        if document is None:
            return None

        return self.model.from_document(document)


class BaseSyncRepository(Generic[ModelT]):
    collection_name: str = ""
    model: type[ModelT]

    def __init__(self, database: Database):
        self.database = database

    def get_by_id(self, document_id: uuid.UUID) -> ModelT | None:
        return self.to_model(self.collection.find_one({"_id": document_id}))

    def get_by_ids(self, document_ids: Sequence[uuid.UUID]) -> list[ModelT]:
        if not document_ids:
            return []

        return self.get_list({"_id": {"$in": list(document_ids)}})

    def get_all(self) -> list[ModelT]:
        return [self.model.from_document(document) for document in self.collection.find({})]

    def save(self, obj: ModelT) -> ModelT:
        document = obj.to_document()
        document_id = document.pop("_id")

        saved_document = self.collection.find_one_and_update(
            {"_id": document_id},
            build_timestamped_update(document),
            upsert = True,
            return_document = ReturnDocument.AFTER,
        )

        return self.model.from_document(saved_document)

    def save_all(self, objs: Sequence[ModelT]) -> list[ModelT]:
        if not objs:
            return []

        operations = []
        for obj in objs:
            document = obj.to_document()
            document_id = document.pop("_id")
            operations.append(
                UpdateOne({"_id": document_id}, build_timestamped_update(document), upsert = True))

        self.collection.bulk_write(operations)

        # $in не гарантирует порядок результатов, поэтому раскладываем по id и
        # возвращаем в порядке аргумента: иначе вызывающий код, сопоставляющий
        # результат с входным списком по позиции, молча перепутает документы.
        saved_documents = self.get_by_ids([obj.id for obj in objs])
        saved_by_id = {saved.id: saved for saved in saved_documents}

        return [saved_by_id[obj.id] for obj in objs]

    @property
    def collection(self) -> Collection:
        return self.database[self.collection_name]

    def get_one_or_none(self, query: dict[str, Any]) -> ModelT | None:
        return self.to_model(self.collection.find_one(query))

    def get_list(self, query: dict[str, Any]) -> list[ModelT]:
        return [self.model.from_document(document) for document in self.collection.find(query)]

    def to_model(self, document: dict[str, Any] | None) -> ModelT | None:
        if document is None:
            return None

        return self.model.from_document(document)
