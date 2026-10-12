import uuid

from app.celery import celery_app
from app.exceptions import ImageDownloadError, DocumentNotFoundError
from app.models.models import IndexState
from app.models.vectors import ImageVector
from app.tasks.common import BaseTask


@celery_app.task(bind=True, base=BaseTask)
def create_embedding(self: BaseTask, document_id: str) -> None:
    try:
        with self.sync_session_manager.start() as session_manager:
            embedding = session_manager.embeddings.get_by_id(uuid.UUID(document_id))

            if embedding is None:
                raise DocumentNotFoundError(f"ImageEmbedding with id {document_id} not found")

            image_bytes = self.image_service.fetch_bytes(embedding.image_path)
            image_vector = self.embedding_service.encode_image(image_bytes)
            image_vector = ImageVector(id=embedding.id, vector=image_vector)

            if embedding.payload:
                image_vector.payload = embedding.payload

            self.qdrant_session_manager.image_vectors.save(image_vector)

            embedding.index_state = IndexState.READY
            embedding.vector = image_vector.vector
            session_manager.embeddings.save(embedding)

    except Exception as e:
        with self.sync_session_manager.start() as session_manager:
            embedding = session_manager.embeddings.get_by_id(uuid.UUID(document_id))
            if embedding:
                embedding.index_state = IndexState.FAILED
                session_manager.embeddings.save(embedding)
        raise e

