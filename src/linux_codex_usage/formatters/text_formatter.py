from __future__ import annotations

from linux_codex_usage.models import ProviderUsage, UsageReport


def format_text(report: UsageReport) -> str:
    if not report.providers:
        return report.error or "No usage data available."

    rows = [_provider_row(provider) for provider in report.providers]
    widths = [
        max(len(row[index]) for row in rows + [HEADER])
        for index in range(len(HEADER))
    ]

    lines = [_format_row(HEADER, widths), _format_row(SEPARATOR, widths)]
    lines.extend(_format_row(row, widths) for row in rows)

    if report.stale:
        lines.append("")
        lines.append(f"Stale data: {report.error or 'using cached result'}")

    return "\n".join(lines)


HEADER = ["Provider", "Status", "Window", "Remaining", "Credits", "Reset"]
SEPARATOR = ["-" * len(item) for item in HEADER]


def _provider_row(provider: ProviderUsage) -> list[str]:
    window = provider.windows[0] if provider.windows else None
    remaining = "-"
    reset = "-"
    window_name = "-"

    if window:
        window_name = window.name
        if window.remaining_percent is not None:
            remaining = f"{window.remaining_percent:g}%"
        reset = window.reset_label or window.resets_at or "-"

    credits = "-"
    if provider.credits:
        if provider.credits.remaining is not None:
            credits = _format_amount(provider.credits.remaining, provider.credits.unit)
        elif provider.credits.used is not None:
            credits = f"used {_format_amount(provider.credits.used, provider.credits.unit)}"

    return [
        provider.label,
        provider.status,
        window_name,
        remaining,
        credits,
        provider.error or reset,
    ]


def _format_row(row: list[str], widths: list[int]) -> str:
    return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))


def _format_amount(value: float, unit: str | None) -> str:
    if unit == "USD":
        return f"${value:.2f}"
    return f"{value:g}{unit or ''}"
