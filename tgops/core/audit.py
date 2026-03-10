"""Append-only JSONL audit logger for TGOps."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

import aiofiles


@dataclass
class AuditEntry:
    """A single audit log entry."""

    event: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    job_id: str | None = None
    group_id: int | None = None
    user_id: int | None = None
    step: str | None = None
    status: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuditEntry":
        data = dict(data)
        if "timestamp" in data and isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        return cls(**data)


class AuditLogger:
    """Append-only JSONL audit logger."""

    def __init__(self, log_path: str):
        self.log_path = os.path.expanduser(log_path)

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    async def log(self, entry: AuditEntry) -> None:
        """Append a single AuditEntry to the JSONL file."""
        self._ensure_dir()
        line = json.dumps(entry.to_dict()) + "\n"
        async with aiofiles.open(self.log_path, mode="a", encoding="utf-8") as f:
            await f.write(line)

    async def read_entries(self, limit: int | None = None) -> list[AuditEntry]:
        """Read audit entries from the log file, newest last."""
        if not os.path.exists(self.log_path):
            return []
        entries: list[AuditEntry] = []
        async with aiofiles.open(self.log_path, mode="r", encoding="utf-8") as f:
            async for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    entries.append(AuditEntry.from_dict(data))
                except (json.JSONDecodeError, TypeError):
                    continue
        if limit is not None:
            entries = entries[-limit:]
        return entries


# Module-level convenience — services create their own AuditLogger instances
def make_audit_logger(log_path: str) -> AuditLogger:
    return AuditLogger(log_path)
