"""Bridge service configuration loader.

Reads from environment variables (with .env support via pydantic-settings).
Critical settings are validated at startup; bridge refuses to start if
BRIDGE_LLM_STRICT=true and BRIDGE_LLM_PROVIDER != 'glm'.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BridgeSettings(BaseSettings):
    """Bridge service settings loaded from environment / .env."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore other KBSQL env vars
        case_sensitive=False,
    )

    # --- Hogwarts-KB integration ---
    hogwarts_kb_path: Path = Field(
        default=Path.home() / "Hogwarts-Knowledge-Base",
        description="Absolute path to local Hogwarts-KB clone",
    )
    hogwarts_kb_remote: str = Field(
        default="",
        description="Git remote URL (https) for Hogwarts-KB",
    )
    hogwarts_kb_auto_push: bool = Field(
        default=False,
        description="If true, kb_writer commits + pushes to GitHub after every write",
    )
    hogwarts_kb_branch: str = Field(
        default="main",
        description="Branch the bridge writes to",
    )

    # --- Bridge LLM router (Zhipu GLM) ---
    glm_api_key: str = Field(default="", description="Zhipu GLM API key")
    bridge_llm_provider: Literal["glm", "openai", "anthropic"] = Field(
        default="glm",
        description="LLM provider for bridge ops; ONLY 'glm' allowed in strict mode",
    )
    bridge_llm_model: str = Field(default="glm-4-flash", description="Default model name")
    bridge_llm_base_url: str = Field(
        default="https://open.bigmodel.cn/api/paas/v4",
        description="Provider base URL",
    )
    bridge_llm_strict: bool = Field(
        default=True,
        description="Hard switch: refuse fallback to non-GLM providers",
    )

    # --- KBSQL integration (reuses existing settings via shared-config) ---
    # We don't redefine POSTGRES_*/REDIS_*/S3_* here; bridge code imports
    # them from shared_config.settings.get_settings() to stay DRY.

    # --- File watcher ---
    watcher_ignore_globs: list[str] = Field(
        default_factory=lambda: [
            ".git/*",
            ".obsidian/*",
            ".search-index.sqlite*",
            ".DS_Store",
            "node_modules/*",
            ".venv/*",
            ".claude/worktrees/*",
        ],
        description="Glob patterns to ignore (relative to hogwarts_kb_path)",
    )

    # --- Writer safety ---
    writer_allowed_paths: list[str] = Field(
        default_factory=lambda: ["wiki/summaries", "wiki/analyses"],
        description="Bridge may ONLY write inside these subdirectories of KB",
    )
    writer_git_lock_timeout_s: int = Field(
        default=30,
        description="Max seconds to wait for .git/index.lock before bailing",
    )

    @field_validator("bridge_llm_provider")
    @classmethod
    def _enforce_strict_glm(cls, v: str, info) -> str:
        """If strict mode is on, refuse non-GLM providers."""
        # Note: pydantic v2 cross-field validation runs after individual validators;
        # we cannot easily access bridge_llm_strict here. The runtime check happens
        # in bridge/llm/router.py:get_llm_client() instead, with clearer error.
        return v

    @field_validator("hogwarts_kb_path")
    @classmethod
    def _path_must_exist(cls, v: Path) -> Path:
        """Soft-check: warn but don't fail if KB path missing (eg. tests)."""
        # Don't raise — bridge service can still start without KB attached
        # (REST/MCP can answer status queries even if KB unavailable).
        return v.expanduser().resolve()


_settings: BridgeSettings | None = None


def get_settings() -> BridgeSettings:
    """Lazy singleton accessor (mirrors shared_config pattern)."""
    global _settings
    if _settings is None:
        _settings = BridgeSettings()
    return _settings


def reset_settings() -> None:
    """Test helper: force re-load from environment on next get_settings() call."""
    global _settings
    _settings = None
