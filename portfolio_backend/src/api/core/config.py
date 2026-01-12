import os
import re
from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # CORS
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"], alias="ALLOWED_ORIGINS")

    # JWT
    jwt_secret: str = Field(default="change-me", alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    # DB
    database_url: Optional[str] = Field(default=None, alias="DATABASE_URL")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")

    def resolve_database_url(self) -> str:
        """
        Resolve the database URL following repository source-of-truth.

        Priority:
        1) DATABASE_URL env var if provided
        2) Read portfolio_database/db_connection.txt (contains: `psql postgresql://...`)
        """
        if self.database_url:
            return self.database_url

        # Locate db_connection.txt relative to this file, without hardcoding ports.
        # src/api/core/config.py -> src/api/core -> src/api -> src -> portfolio_backend -> workspace root
        workspace_root = Path(__file__).resolve().parents[5]
        db_conn_path = workspace_root / "professional-portfolio-dashboard-304348-304357" / "portfolio_database" / "db_connection.txt"
        if not db_conn_path.exists():
            raise RuntimeError(
                "DATABASE_URL not set and portfolio_database/db_connection.txt not found. "
                "Provide DATABASE_URL env var or ensure the database container is present."
            )

        content = db_conn_path.read_text(encoding="utf-8").strip()
        # Expected format: "psql postgresql://user:pass@host:port/db"
        match = re.search(r"(postgresql://\S+)", content)
        if not match:
            raise RuntimeError(
                "portfolio_database/db_connection.txt did not contain a recognizable postgresql:// URL."
            )
        return match.group(1)


settings = Settings()
