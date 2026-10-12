from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.lifespan import lifespan
from app.logging import initialize_logger
from app.middlewares.logging_middleware import LoggingMiddleware


# Приложение владеет клиентом Mongo целиком: создаёт на старте, кладёт
# в app.state и закрывает на остановке. Клиент один на процесс, пул соединений
# внутри него драйвер держит сам.


app = FastAPI(
    title = "Image Generation Service",
    lifespan = lifespan,
)

app.add_middleware(LoggingMiddleware)

initialize_logger(app)


# Главная страница сервису не нужна — отправляем на Swagger UI.
# В схему OpenAPI не включаем: это не часть API.
@app.get("/", include_in_schema = False)
async def root() -> RedirectResponse:
    return RedirectResponse(url = app.docs_url)
