import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_env_file_path(env=None) -> str:
    env_dir = "conf"
    if env:
        return f"{BASE_DIR}/{env_dir}/.env.{env}"
    path = f"{BASE_DIR}/{env_dir}/.env.{os.getenv('ENV', 'dev')}"
    if not os.path.exists(path):
        return f"{BASE_DIR}/{env_dir}/.env"
    return path