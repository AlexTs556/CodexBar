from __future__ import annotations

from linux_codex_usage.models import ProviderUsage, UsageReport


def format_text(report: UsageReport) -> str:
    if not report.providers:
        return report.error or "No usage data available."

    rows = []
    for provider in report.providers:
        rows.extend(_provider_rows(provider))
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


HEADER = ["Provider", "Account", "Source", "Window", "Used", "Remaining", "Reset", "Notes"]
SEPARATOR = ["-" * len(item) for item in HEADER]


def _provider_rows(provider: ProviderUsage) -> list[list[str]]:
    if provider.credits:
        if provider.credits.remaining is not None:
            credits = f"credits {_format_amount(provider.credits.remaining, provider.credits.unit)}"
        elif provider.credits.used is not None:
            credits = f"cost {_format_amount(provider.credits.used, provider.credits.unit)}"
        else:
            credits = ""
    else:
        credits = ""

    if not provider.windows:
        return [[
            provider.label,
            provider.account or "-",
            provider.source or "-",
            "-",
            "-",
            "-",
            "-",
            provider.error or credits or provider.status,
        ]]

    rows = []
    for index, window in enumerate(provider.windows):
        rows.append([
            provider.label if index == 0 else "",
            provider.account or "-" if index == 0 else "",
            provider.source or "-" if index == 0 else "",
            window.name,
            f"{window.used_percent:g}%" if window.used_percent is not None else "-",
            f"{window.remaining_percent:g}%" if window.remaining_percent is not None else "-",
            window.reset_label or window.resets_at or "-",
            provider.error if index == 0 and provider.error else credits if index == 0 else "",
        ])
    return rows


def _provider_row(provider: ProviderUsage) -> list[str]:
    return _provider_rows(provider)[0]


def _legacy_provider_row(provider: ProviderUsage) -> list[str]:
    return [
        provider.label,
        provider.account or "-",
        provider.source or "-",
        "-",
        "-",
        "-",
        "-",
        provider.error or provider.status,
    ]


def _format_row(row: list[str], widths: list[int]) -> str:
    return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))


def _format_amount(value: float, unit: str | None) -> str:
    if unit == "USD":
        return f"${value:.2f}"
    return f"{value:g}{unit or ''}"
