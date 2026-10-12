import uuid

from fastapi import Depends

from app.db.session_manager import AsyncSessionManager, get_async_session_manager
from app.exceptions import DocumentNotFoundError
from app.models.models import ImageEmbedding
from app.schemas.requests import CreateEmbeddingRequest
from app.schemas.responses import EmbeddingResponse


class RestImageEmbeddingService:
    def __init__(self, async_session_manager: AsyncSessionManager, create_embedding_task):
        self.async_session_manager = async_session_manager
        self.create_embedding_task = create_embedding_task

    async def create_embedding(self, request: CreateEmbeddingRequest) -> EmbeddingResponse:
        embedding = ImageEmbedding(
            image_path = request.image_path,
            payload = request.payload,
        )

        async with self.async_session_manager.start() as session_manager:
            saved_embedding = await session_manager.embeddings.save(embedding)

        self.create_embedding_task.delay(str(saved_embedding.id))

        return EmbeddingResponse.to_response(saved_embedding)

    async def get_embedding(self, embedding_id: uuid.UUID) -> EmbeddingResponse:
        async with self.async_session_manager.start() as session_manager:
            embedding = await session_manager.embeddings.get_by_id(embedding_id)

        if embedding is None:
            raise DocumentNotFoundError(f"Нет записи ImageEmbedding с id {embedding_id}.")

        return EmbeddingResponse.to_response(embedding)


def get_rest_image_embedding_service(
        async_session_manager: AsyncSessionManager = Depends(
            get_async_session_manager, use_cache = True)) -> RestImageEmbeddingService:
    from app.tasks.create_embedding_task import create_embedding

    return RestImageEmbeddingService(async_session_manager, create_embedding)
