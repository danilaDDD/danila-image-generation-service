from celery import Celery

# Импорт ради побочного эффекта: модуль подписывает handler на logs/celery.log
# на сигналы Celery, и подписка должна произойти до старта воркера.
import app.logging.celery_logging  # noqa: F401
from settings.settings import load_settings

settings = load_settings()

celery_app = Celery(
        "image_generation",
        broker=settings.CELERY_BROKER_URL,
        # Сюда перечисляются модули с задачами — именно модули, а не пакет:
        # __init__ пакета app.tasks пуст.
        include = [],
)
