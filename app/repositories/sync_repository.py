import uuid
from typing import Sequence

from pymongo import ReturnDocument, UpdateOne

from app.models.models import ImageEmbedding, ImageQuery
from app.repositories.base import BaseSyncRepository, build_timestamped_update


class SyncImageEmbeddingRepository(BaseSyncRepository[ImageEmbedding]):
    collection_name = "image_embeddings"
    model = ImageEmbedding

class SyncImageQueryRepository(BaseSyncRepository[ImageQuery]):
    collection_name = "image_queries"
    model = ImageQuery


