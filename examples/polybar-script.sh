#!/usr/bin/env sh
set -eu

linux-codex-usage cost --provider codex --format json |
  python3 -c 'import json, sys
data = json.load(sys.stdin)
parts = []
for provider in data.get("providers", []):
    label = provider.get("label") or provider.get("provider") or "AI"
    windows = provider.get("windows") or []
    if windows and windows[0].get("remaining_percent") is not None:
        remaining = windows[0]["remaining_percent"]
        parts.append(f"{label} {remaining:g}%")
    elif provider.get("credits") and provider["credits"].get("remaining") is not None:
        unit = provider["credits"].get("unit") or ""
        remaining = provider["credits"]["remaining"]
        parts.append(f"{label} {remaining:g}{unit}")
    else:
        parts.append(label)
print(" | ".join(parts) if parts else "AI usage unavailable")'
