from pydantic import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    UPLOAD_DIR: str = "/tmp/papermorph/uploads"
    DEBUG: bool = True

    class Config:
        env_file = ".env"

settings = Settings()

# Ensure upload directory exists
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
