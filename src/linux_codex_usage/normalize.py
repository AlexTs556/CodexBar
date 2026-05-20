from __future__ import annotations

from typing import Any

from .models import Credits, ProviderUsage, UsageReport, WindowUsage, utc_now_iso


PROVIDER_LIST_KEYS = ("providers", "data", "results", "usage")
WINDOW_KEYS = ("windows", "limits", "rate_limits", "quotas")


def normalize_usage(raw: Any) -> UsageReport:
    provider_items = _extract_provider_items(raw)
    providers = [_normalize_provider(item) for item in provider_items]
    return UsageReport(providers=providers, generated_at=utc_now_iso())


def _extract_provider_items(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [_as_dict(item) for item in raw]

    if not isinstance(raw, dict):
        return [{"provider": "unknown", "label": "Unknown", "error": "unexpected JSON"}]

    for key in PROVIDER_LIST_KEYS:
        value = raw.get(key)
        if isinstance(value, list):
            return [_as_dict(item) for item in value]
        if isinstance(value, dict):
            return _dict_to_provider_items(value)

    if _looks_like_single_provider(raw):
        return [raw]

    return _dict_to_provider_items(raw)


def _dict_to_provider_items(value: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for key, item in value.items():
        provider = _as_dict(item)
        provider.setdefault("provider", str(key))
        provider.setdefault("label", _title_label(str(key)))
        items.append(provider)
    return items


def _normalize_provider(item: dict[str, Any]) -> ProviderUsage:
    usage = item.get("usage") if isinstance(item.get("usage"), dict) else {}
    provider_id = _first_string(item, "provider", "id", "name", default="unknown")
    label = _first_string(item, "label", "display_name", "title", default=None)
    status = _first_string(item, "status", "state", default=None)
    error = _extract_error(item)

    if not status:
        status = "error" if error else "ok"

    return ProviderUsage(
        provider=provider_id,
        label=label or _title_label(provider_id),
        source=_first_string(item, "source", "source_type", "method", default=None),
        status=status,
        updated_at=_first_string(
            item,
            "updated_at",
            "updatedAt",
            "fetched_at",
            "timestamp",
            default=None,
        )
        or _first_string(
            usage,
            "updated_at",
            "updatedAt",
            default=None,
        ),
        account=_first_string(item, "account", "email", "user", "username", default=None)
        or _first_string(usage, "accountEmail", "account", "email", default=None),
        windows=_extract_windows(item),
        credits=_extract_credits(item),
        error=error,
        raw=item,
    )


def _extract_windows(item: dict[str, Any]) -> list[WindowUsage]:
    usage = item.get("usage")
    if isinstance(usage, dict):
        usage_windows = _extract_usage_windows(usage)
        if usage_windows:
            return usage_windows

    for key in WINDOW_KEYS:
        value = item.get(key)
        if isinstance(value, list):
            return [_normalize_window(_as_dict(window), str(index)) for index, window in enumerate(value)]
        if isinstance(value, dict):
            return [
                _normalize_window(_as_dict(window), str(name))
                for name, window in value.items()
            ]

    inline_window = _normalize_window(item, "default")
    if inline_window.used_percent is not None or inline_window.remaining_percent is not None:
        return [inline_window]
    return []


def _extract_usage_windows(usage: dict[str, Any]) -> list[WindowUsage]:
    windows: list[WindowUsage] = []
    for key in ("primary", "secondary", "tertiary"):
        value = usage.get(key)
        if not isinstance(value, dict):
            continue
        window = _normalize_window(value | {"name": _window_name(key, value)}, key)
        windows.append(window)
    return windows


def _window_name(fallback_name: str, item: dict[str, Any]) -> str:
    minutes = _to_float(item.get("windowMinutes"))
    if minutes == 300:
        return "5h"
    if minutes == 10080:
        return "weekly"
    if minutes is not None and minutes >= 60:
        hours = minutes / 60
        if hours.is_integer():
            return f"{int(hours)}h"
    return fallback_name


def _normalize_window(item: dict[str, Any], fallback_name: str) -> WindowUsage:
    name = _first_string(item, "name", "window", "period", default=fallback_name)
    remaining_percent = _first_number(
        item,
        "remaining_percent",
        "remainingPct",
        "percent_remaining",
        default=None,
    )
    used_percent = _first_number(
        item,
        "used_percent",
        "usedPct",
        "percent_used",
        "usage_percent",
        "usagePct",
        "usedPercent",
        default=None,
    )

    if remaining_percent is None and used_percent is not None:
        remaining_percent = max(0.0, 100.0 - used_percent)
    if used_percent is None and remaining_percent is not None:
        used_percent = max(0.0, 100.0 - remaining_percent)

    return WindowUsage(
        name=name,
        used_percent=used_percent,
        remaining_percent=remaining_percent,
        resets_at=_first_string(item, "resets_at", "reset_at", "resetAt", "expires_at", default=None),
        reset_label=_first_string(
            item,
            "reset_label",
            "resetLabel",
            "reset_in",
            "resetIn",
            "resetDescription",
            default=None,
        ),
    )


def _extract_credits(item: dict[str, Any]) -> Credits | None:
    credits = item.get("credits") or item.get("balance") or item.get("cost")
    data = _as_dict(credits) if isinstance(credits, dict) else item

    remaining = _first_number(data, "remaining", "balance", "available", "left", default=None)
    used = _first_number(
        data,
        "used",
        "spent",
        "cost",
        "last30DaysCostUSD",
        "sessionCostUSD",
        default=None,
    )
    total = _first_number(data, "total", "limit", "quota", default=None)
    unit = _first_string(data, "unit", "currency", default=None)

    if unit is None and (
        "last30DaysCostUSD" in data
        or "sessionCostUSD" in data
        or str(data.get("source")) == "local"
    ):
        unit = "USD"

    if remaining is None and used is None and total is None:
        return None

    return Credits(remaining=remaining, used=used, total=total, unit=unit)


def _looks_like_single_provider(raw: dict[str, Any]) -> bool:
    marker_keys = {
        "provider",
        "id",
        "label",
        "source",
        "status",
        "windows",
        "limits",
        "remaining_percent",
        "used_percent",
        "credits",
    }
    return any(key in raw for key in marker_keys)


def _extract_error(item: dict[str, Any]) -> str | None:
    error = item.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if message:
            return str(message)
    if error:
        return str(error)
    message = item.get("message")
    if message:
        return str(message)
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {"value": value}


def _first_string(data: dict[str, Any], *keys: str, default: str | None) -> str | None:
    for key in keys:
        value = data.get(key)
        if value is not None and value != "":
            return str(value)
    return default


def _first_number(data: dict[str, Any], *keys: str, default: float | None) -> float | None:
    for key in keys:
        value = data.get(key)
        number = _to_float(value)
        if number is not None:
            return number
    return default


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip().removesuffix("%")
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _title_label(provider_id: str) -> str:
    return provider_id.replace("_", " ").replace("-", " ").title()
