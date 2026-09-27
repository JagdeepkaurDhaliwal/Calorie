from pathlib import Path
import os
from pydantic import model_validator
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

    @model_validator(mode="after")
    def ensure_serverless_safe_paths(self) -> "Settings":
        is_serverless = bool(
            os.environ.get("VERCEL")
            or os.environ.get("AWS_LAMBDA_FUNCTION_NAME")
            or os.environ.get("LAMBDA_TASK_ROOT")
        )
        if is_serverless and self.database_url.startswith("sqlite"):
            # Ensure SQLite is stored in /tmp on read-only serverless filesystems
            if not ("/tmp/" in self.database_url or ":memory:" in self.database_url):
                self.database_url = "sqlite:////tmp/caloriecast.db"
        return self

    @property
    def artifact_path(self) -> Path:
        path = Path(self.artifact_dir)
        if not path.is_absolute():
            path = ROOT_DIR / path
        return path


settings = Settings()

