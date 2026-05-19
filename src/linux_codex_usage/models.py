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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WindowUsage":
        return cls(
            name=str(data.get("name") or "default"),
            used_percent=_optional_float(data.get("used_percent")),
            remaining_percent=_optional_float(data.get("remaining_percent")),
            resets_at=_optional_string(data.get("resets_at")),
            reset_label=_optional_string(data.get("reset_label")),
        )


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Credits":
        return cls(
            remaining=_optional_float(data.get("remaining")),
            used=_optional_float(data.get("used")),
            total=_optional_float(data.get("total")),
            unit=_optional_string(data.get("unit")),
        )


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProviderUsage":
        credits = data.get("credits")
        return cls(
            provider=str(data.get("provider") or "unknown"),
            label=str(data.get("label") or data.get("provider") or "Unknown"),
            source=_optional_string(data.get("source")),
            status=str(data.get("status") or "ok"),
            updated_at=_optional_string(data.get("updated_at")),
            account=_optional_string(data.get("account")),
            windows=[
                WindowUsage.from_dict(window)
                for window in data.get("windows", [])
                if isinstance(window, dict)
            ],
            credits=Credits.from_dict(credits) if isinstance(credits, dict) else None,
            error=_optional_string(data.get("error")),
            raw=data.get("raw") if isinstance(data.get("raw"), dict) else None,
        )


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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UsageReport":
        return cls(
            providers=[
                ProviderUsage.from_dict(provider)
                for provider in data.get("providers", [])
                if isinstance(provider, dict)
            ],
            generated_at=str(data.get("generated_at") or utc_now_iso()),
            stale=bool(data.get("stale", False)),
            error=_optional_string(data.get("error")),
        )


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)
