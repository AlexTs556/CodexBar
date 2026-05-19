from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from linux_codex_usage.formatters.text_formatter import format_text
from linux_codex_usage.models import ProviderUsage, UsageReport


def format_cost_text(report: UsageReport) -> str:
    if not report.providers:
        return report.error or "No cost data available."

    sections = []
    for provider in report.providers:
        if not _is_cost_provider(provider):
            sections.append(format_text(UsageReport(providers=[provider])))
            continue
        sections.append(_provider_cost_section(provider))

    if report.stale:
        sections.append(f"Stale data: {report.error or 'using cached result'}")

    return "\n\n".join(section for section in sections if section)


def _is_cost_provider(provider: ProviderUsage) -> bool:
    raw = provider.raw or {}
    return bool(raw.get("daily")) or provider.source == "local"


def _provider_cost_section(provider: ProviderUsage) -> str:
    raw = provider.raw or {}
    daily = _daily_rows(raw.get("daily"))
    latest_day = _latest_date(daily)
    today_rows = [row for row in daily if row["date"] == latest_day] if latest_day else []
    last_7_rows = _rows_since(daily, latest_day, days=7) if latest_day else []

    total_cost = _number(raw.get("last30DaysCostUSD")) or _sum_cost(daily)
    total_tokens = _integer(raw.get("last30DaysTokens")) or _sum_tokens(daily)
    today_cost = _sum_cost(today_rows)
    today_tokens = _sum_tokens(today_rows)
    last_7_cost = _sum_cost(last_7_rows)
    last_7_tokens = _sum_tokens(last_7_rows)

    lines = [
        f"{provider.label} cost summary",
        f"Source: {provider.source or '-'}",
    ]
    if provider.updated_at:
        lines.append(f"Updated: {provider.updated_at}")
    lines.extend(
        [
            "",
            f"Today:      {_money(today_cost)} / {_tokens(today_tokens)}",
            f"Last 7d:    {_money(last_7_cost)} / {_tokens(last_7_tokens)}",
            f"Last 30d:   {_money(total_cost)} / {_tokens(total_tokens)}",
        ]
    )

    model_rows = _model_breakdown(daily)
    if model_rows:
        lines.extend(["", "Top models:"])
        for name, cost, tokens in model_rows[:5]:
            lines.append(f"  {name.ljust(16)} {_money(cost).rjust(10)}  {_tokens(tokens)}")

    recent_rows = sorted(daily, key=lambda row: row["date"], reverse=True)[:10]
    if recent_rows:
        lines.extend(["", "Recent days:"])
        table = [["Date", "Cost", "Tokens", "Models"]]
        for row in recent_rows:
            table.append(
                [
                    row["date"].isoformat(),
                    _money(row["cost"]),
                    _tokens(row["tokens"]),
                    ", ".join(row["models"]) or "-",
                ]
            )
        lines.extend(_table(table))

    if provider.error:
        lines.extend(["", f"Error: {provider.error}"])

    return "\n".join(lines)


def _daily_rows(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        day = _date(item.get("date"))
        if not day:
            continue
        rows.append(
            {
                "date": day,
                "cost": _number(item.get("totalCost")) or 0.0,
                "tokens": _integer(item.get("totalTokens")) or 0,
                "models": [str(model) for model in item.get("modelsUsed", [])],
                "model_breakdowns": item.get("modelBreakdowns", []),
            }
        )
    return rows


def _latest_date(rows: list[dict[str, Any]]) -> date | None:
    if not rows:
        return None
    return max(row["date"] for row in rows)


def _rows_since(
    rows: list[dict[str, Any]],
    latest_day: date,
    days: int,
) -> list[dict[str, Any]]:
    start = latest_day - timedelta(days=days - 1)
    return [row for row in rows if start <= row["date"] <= latest_day]


def _model_breakdown(rows: list[dict[str, Any]]) -> list[tuple[str, float, int]]:
    costs: dict[str, float] = defaultdict(float)
    tokens: dict[str, int] = defaultdict(int)

    for row in rows:
        for breakdown in row["model_breakdowns"]:
            if not isinstance(breakdown, dict):
                continue
            name = str(breakdown.get("modelName") or "unknown")
            costs[name] += _number(breakdown.get("cost")) or 0.0
            tokens[name] += _integer(breakdown.get("totalTokens")) or 0

    return sorted(
        ((name, cost, tokens[name]) for name, cost in costs.items()),
        key=lambda item: item[1],
        reverse=True,
    )


def _table(rows: list[list[str]]) -> list[str]:
    widths = [
        max(len(row[index]) for row in rows)
        for index in range(len(rows[0]))
    ]
    return [
        "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]


def _sum_cost(rows: list[dict[str, Any]]) -> float:
    return sum(row["cost"] for row in rows)


def _sum_tokens(rows: list[dict[str, Any]]) -> int:
    return sum(row["tokens"] for row in rows)


def _date(value: Any) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _integer(value: Any) -> int | None:
    number = _number(value)
    return int(number) if number is not None else None


def _money(value: float) -> str:
    return f"${value:,.2f}"


def _tokens(value: int) -> str:
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M tokens"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K tokens"
    return f"{value} tokens"
