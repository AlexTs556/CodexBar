from __future__ import annotations

import json

from linux_codex_usage.models import ProviderUsage, UsageReport


def format_waybar(
    report: UsageReport,
    warning_threshold: float = 80.0,
    critical_threshold: float = 95.0,
) -> str:
    payload = {
        "text": _text(report),
        "tooltip": _tooltip(report),
        "class": _css_class(report, warning_threshold, critical_threshold),
    }
    return json.dumps(payload, ensure_ascii=False)


def _text(report: UsageReport) -> str:
    if not report.providers:
        return "AI usage unavailable"

    parts = [_provider_summary(provider) for provider in report.providers]
    prefix = "cached " if report.stale else ""
    return prefix + " | ".join(part for part in parts if part)


def _tooltip(report: UsageReport) -> str:
    lines: list[str] = []
    if report.error:
        lines.append(report.error)
    for provider in report.providers:
        lines.append(_provider_tooltip(provider))
    return "\n".join(line for line in lines if line)


def _provider_summary(provider: ProviderUsage) -> str:
    if provider.error and not provider.windows and not provider.credits:
        return f"{provider.label} error"

    window = provider.windows[0] if provider.windows else None
    if window and window.remaining_percent is not None:
        return f"{provider.label} {window.remaining_percent:g}%"

    if provider.credits and provider.credits.remaining is not None:
        unit = provider.credits.unit or ""
        return f"{provider.label} {provider.credits.remaining:g}{unit}"

    return provider.label


def _provider_tooltip(provider: ProviderUsage) -> str:
    lines = [f"{provider.label}: {provider.status}"]
    if provider.account:
        lines.append(f"Account: {provider.account}")
    for window in provider.windows:
        pieces = [window.name]
        if window.remaining_percent is not None:
            pieces.append(f"{window.remaining_percent:g}% remaining")
        if window.used_percent is not None:
            pieces.append(f"{window.used_percent:g}% used")
        if window.reset_label or window.resets_at:
            pieces.append(f"reset {window.reset_label or window.resets_at}")
        lines.append(" - " + ", ".join(pieces))
    if provider.credits and provider.credits.remaining is not None:
        unit = provider.credits.unit or ""
        lines.append(f"Credits: {provider.credits.remaining:g}{unit}")
    if provider.error:
        lines.append(f"Error: {provider.error}")
    return "\n".join(lines)


def _css_class(
    report: UsageReport,
    warning_threshold: float,
    critical_threshold: float,
) -> str:
    if report.stale:
        return "stale"
    if report.error and not report.providers:
        return "error"
    if any(provider.status == "error" for provider in report.providers):
        return "error"

    max_used = 0.0
    for provider in report.providers:
        for window in provider.windows:
            if window.used_percent is not None:
                max_used = max(max_used, window.used_percent)

    if max_used >= critical_threshold:
        return "critical"
    if max_used >= warning_threshold:
        return "warning"
    return "ok"

