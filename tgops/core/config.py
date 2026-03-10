"""Pydantic settings for TGOps — reads from env vars and optionally tgops.yaml."""

from __future__ import annotations

import os
from typing import Any

import yaml
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main configuration for TGOps."""

    model_config = SettingsConfigDict(
        env_prefix="TGOPS_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Required Telegram credentials
    api_id: int = Field(..., description="Telegram API ID")
    api_hash: str = Field(..., description="Telegram API hash")
    phone: str = Field(..., description="Phone number for Telegram account")

    # Session & paths
    session_path: str = Field(
        default="~/.tgops/sessions/org_account",
        description="Path to the Hydrogram session file",
    )
    audit_log_path: str = Field(
        default="~/.tgops/audit.jsonl",
        description="Path to the append-only audit log",
    )
    jobs_dir: str = Field(
        default="~/.tgops/jobs",
        description="Directory for migration job files",
    )
    offboarding_dir: str = Field(
        default="~/.tgops/offboarding",
        description="Directory for offboarding job files",
    )

    # Rate limiting
    base_delay_seconds: float = Field(
        default=2.5,
        description="Base delay between API calls (seconds)",
    )
    max_flood_retries: int = Field(
        default=3,
        description="Maximum number of FloodWait retry attempts",
    )
    emergency_delay_seconds: float = Field(
        default=1.0,
        description="Minimal delay for emergency operations (seconds). 1.0s floor — ~30 ban-type actions/minute is the safe community-documented threshold.",
    )

    # Feature flags
    dry_run: bool = Field(
        default=False,
        description="If True, skip all destructive API calls",
    )

    # Webhook alerts
    webhook_url: str = Field(
        default="",
        description="URL for webhook alerts (Telegram bot or Slack)",
    )
    webhook_type: str = Field(
        default="telegram",
        description="Webhook type: 'telegram' or 'slack'",
    )
    api_key: str = Field(
        default="",
        description="REST API bearer token. Empty = no auth (local use only)",
    )

    # Emergency behaviour
    emergency_rotate_invites: bool = Field(
        default=True,
        description="Rotate all invite links after emergency offboarding",
    )

    # Message templates
    default_offboard_message: str = Field(
        default="",
        description="Default message sent to offboarded members",
    )
    archive_message: str = Field(
        default="This group has been archived.\nPlease join our new group: {invite_link}",
        description="Message pinned in archived groups",
    )
    archive_prefix: str = Field(
        default="[ARCHIVED]",
        description="Prefix added to archived group titles",
    )
    redirect_interval_seconds: int = Field(
        default=3600,
        description="How often (seconds) the redirect handler fires",
    )

    @field_validator("session_path", "audit_log_path", "jobs_dir", "offboarding_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str) -> str:
        return os.path.expanduser(v)


def load_config(config_path: str | None = None) -> Settings:
    """
    Load settings by:
    1. Reading optional YAML file (tgops.yaml or config_path)
    2. Overlaying env vars on top (env vars win)
    """
    yaml_values: dict[str, Any] = {}

    candidates = []
    if config_path:
        candidates.append(config_path)
    else:
        candidates.extend(["tgops.yaml", "tgops.yml", os.path.expanduser("~/.tgops/tgops.yaml")])

    for candidate in candidates:
        expanded = os.path.expanduser(candidate)
        if os.path.isfile(expanded):
            with open(expanded) as f:
                loaded = yaml.safe_load(f) or {}
                yaml_values = {k.lower(): v for k, v in loaded.items()}
            break

    # Build a Settings object; env vars in SettingsConfigDict will override yaml values
    # We pass yaml values as init kwargs (lowest priority), env vars override via model_config
    return Settings(**yaml_values)
