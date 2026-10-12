import uuid
from typing import Sequence

from fastapi import Depends

from app.db.qdrant_session_manager import (
    AsyncQdrantSessionManager,
    get_async_qdrant_session_manager,
)
from app.db.session_manager import AsyncSessionManager, get_async_session_manager
from app.exceptions import ImageVectorNotFoundError, ImageQueryNotFoundError
from app.models.models import ResultLine
from app.models.vectors import ImageVectorMatch
from app.schemas.requests import CreateImageQueryRequest
from app.schemas.responses import ImageQueryResponse, ImageSearchResponse
from app.utils.result_line_utils import build_result_lines
from settings.settings import load_settings, Settings


class RestImageQueryService:
    DEFAULT_SEARCH_LIMIT = 5

    def __init__(self,
                 settings: Settings,
                 async_session_manager: AsyncSessionManager,
                 qdrant_session_manager: AsyncQdrantSessionManager,
                 processing_query_task):
        self.session_manager = async_session_manager
        self.qdrant_session_manager = qdrant_session_manager
        self.processing_query_task = processing_query_task
        self.settings = settings

    async def create_image_query(self, request: CreateImageQueryRequest) -> ImageQueryResponse:
        query = request.to_query_model(
            default_limit = self.settings.SEARCH_LIMIT,
            default_min_score = self.settings.MIN_SCORE,
        )

        async with self.session_manager.start() as session_manager:
            saved_query = await session_manager.queries.save(query)

        self.processing_query_task.delay(str(saved_query.id))

        return ImageQueryResponse.of(saved_query)

    async def find_similar_by_image(self,
                                    image_uuid: uuid.UUID,
                                    limit: int = DEFAULT_SEARCH_LIMIT,) -> ImageSearchResponse:
        image_vectors = self.qdrant_session_manager.image_vectors

        source_vector = await image_vectors.get_by_id(image_uuid)

        if source_vector is None:
            raise ImageVectorNotFoundError(
                f"Для картинки {image_uuid} нет вектора: она не существует или ещё не "
                f"проиндексирована."
            )

        matches = await image_vectors.search(
            source_vector.vector,
            limit = limit,
            exclude_ids = [image_uuid],
            min_score = self.settings.MIN_SCORE,
        )

        return ImageSearchResponse(
            image_uuid = image_uuid,
            results = await self._build_result_lines(matches),
        )

    async def _build_result_lines(self,
                                  matches: Sequence[ImageVectorMatch]) -> list[ResultLine]:
        if not matches:
            return []

        async with self.session_manager.start() as session_manager:
            embeddings = await session_manager.embeddings.get_by_ids(
                [match.id for match in matches])

        return build_result_lines(matches, embeddings)

    async def get_image_query(self, query_id: uuid.UUID):
        async with self.session_manager.start() as session_manager:
            query = await session_manager.queries.get_by_id(query_id)
            if query is None:
                raise ImageQueryNotFoundError(f"query by {query_id} not found")

            return ImageQueryResponse.of(query)


def get_rest_image_query_service(
        settings = Depends(load_settings),
        async_session_manager: AsyncSessionManager = Depends(
            get_async_session_manager, use_cache = True),
        qdrant_session_manager: AsyncQdrantSessionManager = Depends(
            get_async_qdrant_session_manager)) -> RestImageQueryService:
    from app.tasks.processing_query_task import process_query

    return RestImageQueryService(settings, async_session_manager, qdrant_session_manager, process_query)
