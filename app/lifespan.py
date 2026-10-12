from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.connection import create_async_mongo_client, create_async_database_factory
from app.db.indexes import ensure_indexes
from settings.settings import load_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    mongo_client = create_async_mongo_client(settings)

    app.state.mongo_client = mongo_client
    app.state.async_database_factory = create_async_database_factory(mongo_client, settings)

    # Mongo сама индексы не заводит, а create_indexes идемпотентен —
    # поэтому вызывается на каждом старте.
    await ensure_indexes(app.state.async_database_factory())

    yield

    await mongo_client.close()
