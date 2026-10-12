import pytest

from settings.settings import Settings

@pytest.mark.unit
def test_env():
    import os
    assert os.getenv('ENV') == 'test'

@pytest.mark.unit
def test_load_settings_with_test_env(settings: Settings):
    assert settings is not None
    assert settings.ENV == "test"
    # Регистронезависимо: имя тестовой базы может быть и image_generation_test,
    # и imageGenerationTestDB. Смысл проверки — не дать тестам уйти в боевую базу.
    assert "test" in settings.MONGO_DB_NAME.lower()
