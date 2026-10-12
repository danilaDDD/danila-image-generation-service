import os
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from settings.path import get_env_file_path


class Settings(BaseSettings):
    ENV: str = Field(default="dev")
    DEBUG: bool = Field(default=False)

    MONGO_HOST: str = Field(default="localhost")
    MONGO_PORT: int = Field(default=27018)
    MONGO_DB_NAME: str = Field(default="image_generation")
    MONGO_USER: str = Field(default="")
    MONGO_PASSWORD: str = Field(default="")
    MONGO_AUTH_SOURCE: str = Field(default="admin")

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_URL: str = "redis://localhost:6379/1"

    def get_mongo_url(self) -> str:
        if not self.MONGO_USER:
            return f"mongodb://{self.MONGO_HOST}:{self.MONGO_PORT}/"

        credentials = f"{quote_plus(self.MONGO_USER)}:{quote_plus(self.MONGO_PASSWORD)}"

        return (f"mongodb://{credentials}@{self.MONGO_HOST}:{self.MONGO_PORT}/"
                f"?authSource={self.MONGO_AUTH_SOURCE}")

    model_config = SettingsConfigDict(
        env_file_encoding = 'utf-8',
        extra = 'ignore',
    )


def load_settings() -> Settings:
    env = os.getenv('ENV', 'dev')
    env_path = get_env_file_path(env=env)

    return Settings(_env_file=env_path)