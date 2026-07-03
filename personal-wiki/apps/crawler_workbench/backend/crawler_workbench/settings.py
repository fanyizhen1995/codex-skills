from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PW_WORKBENCH_", arbitrary_types_allowed=True)

    repo_root: Path = Field(default_factory=lambda: Path.cwd().resolve())
    state_dir: Path | None = None
    bind_host: str = "0.0.0.0"
    bind_port: int = 8765
    max_auto_ingest_bytes: int = 2_000_000
    scheduler_interval_seconds: int = 60
    codex_command: str = "codex"

    @property
    def wiki_root(self) -> Path:
        return self.repo_root / "personal-wiki"

    @property
    def resolved_state_dir(self) -> Path:
        return self.state_dir or (self.repo_root / ".personal-wiki-workbench")

    @property
    def database_path(self) -> Path:
        return self.resolved_state_dir / "workbench.sqlite3"

    @property
    def sources_yaml_path(self) -> Path:
        return self.resolved_state_dir / "sources.yaml"

    @property
    def secrets_key_path(self) -> Path:
        return self.resolved_state_dir / "secrets.key"

    @property
    def trusted_network_warning(self) -> str:
        return "No login is enabled. Expose this service only on a trusted network."
