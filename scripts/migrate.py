#!/usr/bin/env python
"""Накат индексов Mongo — аналог `alembic upgrade head` для этого сервиса.

    python scripts/migrate.py                # окружение dev (conf/.env.dev)
    python scripts/migrate.py --env test     # окружение test (conf/.env.test)
    ENV=test python scripts/migrate.py       # то же самое через переменную окружения
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.connection import (  # noqa: E402
    create_sync_database_factory,
    create_sync_mongo_client,
)
from app.db.indexes import ensure_indexes_sync  # noqa: E402
from pymongo.database import Database  # noqa: E402
from settings.path import get_env_file_path  # noqa: E402
from settings.settings import Settings, load_settings  # noqa: E402

DEFAULT_ENV = "dev"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description = "Применяет индексы Mongo для выбранного окружения.",
    )
    parser.add_argument(
        "--env",
        default = os.getenv("ENV", DEFAULT_ENV),
        help = f"имя окружения из conf/.env.<env> "
               f"(по умолчанию значение ENV или «{DEFAULT_ENV}»)",
    )

    return parser.parse_args()


def migrate(settings: Settings) -> None:
    mongo_client = create_sync_mongo_client(settings)

    try:
        migrate_mongo(create_sync_database_factory(mongo_client, settings)())
    finally:
        mongo_client.close()


def migrate_mongo(database: Database) -> None:
    index_names = ensure_indexes_sync(database)

    print(f"Mongo: база {database.name}, индексы {', '.join(index_names) or '—'}")


def main() -> int:
    args = parse_args()

    os.environ["ENV"] = args.env

    env_file_path = get_env_file_path(env = args.env)
    if not os.path.exists(env_file_path):
        print(f"Нет файла окружения {env_file_path}", file = sys.stderr)

        return 1

    settings = load_settings()

    print(f"Окружение {args.env}: mongo {settings.MONGO_HOST}:{settings.MONGO_PORT}")

    migrate(settings)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
