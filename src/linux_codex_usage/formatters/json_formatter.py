from __future__ import annotations

import json

from linux_codex_usage.models import UsageReport


def format_json(report: UsageReport, pretty: bool = False) -> str:
    indent = 2 if pretty else None
    return json.dumps(report.to_dict(), ensure_ascii=False, indent=indent)

