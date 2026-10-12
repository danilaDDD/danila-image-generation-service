import os

os.environ['ENV'] = 'test'

import pytest

from app.db.connection import (
    create_async_database_factory,
    create_async_mongo_client,
    create_sync_database_factory,
    create_sync_mongo_client,
)
from settings.settings import load_settings, Settings


@pytest.fixture(scope="session", autouse=True)
def setup_all():
    os.environ['ENV'] = 'test'
    yield


@pytest.fixture(scope="module")
def settings() -> Settings:
    return load_settings()


@pytest.fixture(scope="session")
def session_settings() -> Settings:
    os.environ['ENV'] = 'test'

    return load_settings()


# Клиенты живут на всю сессию тестов и закрываются здесь же: это единственный
# владелец клиентов в тестовом процессе, поэтому lifespan приложения или сигналы
# воркера не могут закрыть клиент, которым ещё пользуются тесты.
@pytest.fixture(scope="session")
async def test_mongo_client(session_settings):
    mongo_client = create_async_mongo_client(session_settings)

    yield mongo_client

    await mongo_client.close()


@pytest.fixture(scope="session")
def test_sync_mongo_client(session_settings):
    mongo_client = create_sync_mongo_client(session_settings)

    yield mongo_client

    mongo_client.close()


@pytest.fixture(scope="session")
def test_database_factory(session_settings, test_mongo_client):
    return create_async_database_factory(test_mongo_client, session_settings)


@pytest.fixture(scope="session")
def test_sync_database_factory(session_settings, test_sync_mongo_client):
    return create_sync_database_factory(test_sync_mongo_client, session_settings)
