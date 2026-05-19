from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from .models import UsageReport


def default_cache_path() -> Path:
    cache_home = os.environ.get("XDG_CACHE_HOME")
    base = Path(cache_home) if cache_home else Path.home() / ".cache"
    return base / "linux-codex-usage" / "status.json"


@dataclass(slots=True)
class UsageCache:
    path: Path

    @classmethod
    def default(cls) -> "UsageCache":
        return cls(default_cache_path())

    def save(self, report: UsageReport) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(
                json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError:
            return

    def load(self) -> UsageReport | None:
        if not self.path.exists():
            return None

        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

        if not isinstance(data, dict):
            return None

        return UsageReport.from_dict(data)
