from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_REPO_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- LLM model to invoke----------------------------------------------------------
    ANTHROPIC_MODEL: str = "claude-sonnet-4-6"

    # --- Input limits -------------------------------------------
    MAX_DOCUMENT_CHARS: int = 500_000
    MAX_QUESTION_CHARS: int = 2_000

    # --- Document storage -------------------------------------------
    DOCUMENT_DIR: Path = _REPO_ROOT

    @computed_field
    @property
    def document_path(self) -> Path:
        """Full path to the stored document file."""
        return self.DOCUMENT_DIR / "document.txt"


settings = Settings()
