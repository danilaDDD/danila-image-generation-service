import uuid

from app.celery import celery_app
from app.db.session_manager import SyncSessionManager
from app.exceptions import ImageQueryNotFoundError
from app.models.models import ImageQueryStatus, ImageQuery, ResultLine
from app.models.vectors import ImageVectorMatch
from app.tasks.common import BaseTask
from app.utils.result_line_utils import build_result_lines


def get_image_vector(self: BaseTask, session_manager: SyncSessionManager, query: ImageQuery):
    img_bytes = self.image_service.fetch_bytes(query.image_path)
    vector = self.embedding_service.encode_image(img_bytes)
    return vector


def get_result_lines(matches: list[ImageVectorMatch],
                     session_manager: SyncSessionManager) -> list[ResultLine]:
    if not matches:
        return []

    embeddings = session_manager.embeddings.get_by_ids([match.id for match in matches])

    return build_result_lines(matches, embeddings)


@celery_app.task(bind=True, base=BaseTask)
def process_query(self: BaseTask, query_id: str) -> None:
    try:
        with self.sync_session_manager.start() as session_manager:
            query = session_manager.queries.get_by_id(uuid.UUID(query_id))

            if query is None:
                raise ImageQueryNotFoundError(f"ImageQuery with id {query_id} not found")

            if query.image_path:
                vector = get_image_vector(self, session_manager, query)
            elif query.text:
                vector = self.embedding_service.encode_text(query.text)
            else:
                # Без ветки else vector остался бы несвязанным и падал бы
                # NameError'ом ниже вместо внятной ошибки.
                raise ValueError(
                    f"ImageQuery {query_id} не содержит ни image_path, ни text: "
                    f"искать нечего."
                )

            matches = self.qdrant_session_manager.image_vectors.search(
                vector,
                limit=query.limit,
                filters=query.filters,
                min_score=query.min_score,
            )

            result_lines = get_result_lines(matches, session_manager)
            query.results = result_lines
            query.status = ImageQueryStatus.READY
            session_manager.queries.save(query)

    except Exception as e:
        with self.sync_session_manager.start() as session_manager:
            query = session_manager.queries.get_by_id(uuid.UUID(query_id))
            if query:
                query.status = ImageQueryStatus.FAILED
                session_manager.queries.save(query)
        raise e
