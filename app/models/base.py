import uuid
from datetime import datetime
from typing import Any, ClassVar, Self

from pydantic import BaseModel, ConfigDict, Field


class AuditedDocument(BaseModel):
    model_config = ConfigDict(populate_by_name = True, use_enum_values = False)

    # Временные метки пишет сервер Mongo через $$NOW (см. app/repositories/base.py).
    # Здесь они только читаются: у свежесозданной модели их ещё нет,
    # после save() репозиторий возвращает модель с проставленными значениями.
    TIMESTAMP_FIELDS: ClassVar[set[str]] = {"created_at", "updated_at"}

    id: uuid.UUID = Field(default_factory = uuid.uuid4, alias = "_id")
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_document(self) -> dict[str, Any]:
        return self.model_dump(by_alias = True, exclude = self.TIMESTAMP_FIELDS)

    @classmethod
    def from_document(cls, document: dict[str, Any]) -> Self:
        return cls.model_validate(document)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"