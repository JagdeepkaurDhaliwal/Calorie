from pathlib import Path
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:////tmp/caloriecast.db" if os.environ.get("VERCEL") else "sqlite:///./caloriecast.db"
    jwt_secret: str = "change-me"
    jwt_expire_minutes: int = 60
    admin_email: str = "admin@example.com"
    admin_password: str = "change-me-too"
    max_upload_mb: int = 10
    artifact_dir: str = "ml/artifacts"
    log_level: str = "INFO"
    cors_origins: str = "*"

    @property
    def artifact_path(self) -> Path:
        path = Path(self.artifact_dir)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path


settings = Settings()
