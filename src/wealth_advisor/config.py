from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WEALTH_ADVISOR_", extra="ignore", env_file=".env"
    )

    app_name: str = "Wealth Advisor Assistant"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    llm_provider: str = "ollama"
    llm_model: str = "llama3.2"
    llm_api_base: str = "http://localhost:11434"
    llm_api_key: str | None = "ollama"
    llm_temperature: float = 0.2
    llm_timeout_seconds: int = 45
    input_dir: Path = Field(default=Path("input"))
    output_dir: Path = Field(default=Path("output"))
    data_dir: Path = Field(default=Path("input"))
    memory_dir: Path = Field(default=Path("output") / "memory")
    approval_mode: str = "manual"
    approval_timeout_seconds: int = 300
    crm_failure_rate: float = 0.0


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.input_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.memory_dir.mkdir(parents=True, exist_ok=True)
    return settings
