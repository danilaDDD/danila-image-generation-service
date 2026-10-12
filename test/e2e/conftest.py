import pytest
from httpx import ASGITransport, AsyncClient

from app.db.indexes import ensure_indexes
from app.main import app

BASE_URL = "http://e2e"


# Приложение поднимается без lifespan. Клиентом Mongo в тестах владеют
# session-фикстуры из test/conftest.py, а lifespan создал бы свой и закрыл его на
# выходе — вместе с тем, которым ещё пользуются остальные тесты. Поэтому в
# app.state кладётся тот же клиент, что и у всех: зависимости приложения
# (get_async_database_factory) читают его оттуда же, что и в проде, —
# подменять их через dependency_overrides не нужно.
@pytest.fixture(scope = "session")
async def e2e_app(test_database_factory):
    app.state.async_database_factory = test_database_factory

    # В проде индексы заводит lifespan; здесь его нет, а вызов идемпотентен.
    await ensure_indexes(test_database_factory())

    return app


# Запрос идёт через ASGI прямо в приложение, без сети и без поднятого uvicorn:
# проверяется весь путь — роутинг, валидация, зависимости, сервис, хранилище.
@pytest.fixture(scope = "session")
async def api_client(e2e_app):
    async with AsyncClient(transport = ASGITransport(app = e2e_app),
                           base_url = BASE_URL) as client:
        yield client
