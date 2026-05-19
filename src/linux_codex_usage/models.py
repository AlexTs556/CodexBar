from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


@dataclass(slots=True)
class WindowUsage:
    name: str
    used_percent: float | None = None
    remaining_percent: float | None = None
    resets_at: str | None = None
    reset_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "used_percent": self.used_percent,
            "remaining_percent": self.remaining_percent,
            "resets_at": self.resets_at,
            "reset_label": self.reset_label,
        }


@dataclass(slots=True)
class Credits:
    remaining: float | None = None
    used: float | None = None
    total: float | None = None
    unit: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "remaining": self.remaining,
            "used": self.used,
            "total": self.total,
            "unit": self.unit,
        }


@dataclass(slots=True)
class ProviderUsage:
    provider: str
    label: str
    source: str | None = None
    status: str = "ok"
    updated_at: str | None = None
    account: str | None = None
    windows: list[WindowUsage] = field(default_factory=list)
    credits: Credits | None = None
    error: str | None = None
    raw: dict[str, Any] | None = None

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        data = {
            "provider": self.provider,
            "label": self.label,
            "source": self.source,
            "status": self.status,
            "updated_at": self.updated_at,
            "account": self.account,
            "windows": [window.to_dict() for window in self.windows],
            "credits": self.credits.to_dict() if self.credits else None,
            "error": self.error,
        }
        if include_raw:
            data["raw"] = self.raw
        return data


@dataclass(slots=True)
class UsageReport:
    providers: list[ProviderUsage]
    generated_at: str = field(default_factory=utc_now_iso)
    stale: bool = False
    error: str | None = None

    def to_dict(self, include_raw: bool = False) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "stale": self.stale,
            "error": self.error,
            "providers": [
                provider.to_dict(include_raw=include_raw) for provider in self.providers
            ],
        }

