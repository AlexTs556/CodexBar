# Linux Codex Usage Monitor

Linux-friendly data layer for AI coding usage limits and balances.

This project is not a macOS CodexBar UI port. The first version wraps the existing `codexbar` CLI and exposes normalized output for terminal usage, Waybar, Polybar, scripts, and later a tray/daemon UI.

See [LINUX_CODEX_USAGE_PLAN.md](LINUX_CODEX_USAGE_PLAN.md) for the implementation roadmap.

## Requirements

- Python 3.11 or newer.
- `codexbar` available in `PATH`, or configured with `codexbar_path`.
- Provider authentication/configuration handled by upstream CodexBar.

## Install For Development

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

## Basic Usage

```bash
linux-codex-usage status
linux-codex-usage status --format json --pretty
linux-codex-usage status --format waybar
linux-codex-usage status --provider codex --provider claude
linux-codex-usage status --provider codex --source cli
linux-codex-usage cost --provider codex
linux-codex-usage cost --provider codex --format waybar
```

The command runs:

```bash
codexbar usage --format json --provider all
```

or the selected providers passed with `--provider`.

If `codexbar` fails and a previous successful result exists, the cached result is returned with `stale = true`.

## Configuration

Create the default config:

```bash
linux-codex-usage config init
```

Default path:

```text
~/.config/linux-codex-usage/config.toml
```

Example:

```toml
providers = ["all"]
warning_threshold = 80
critical_threshold = 95
use_cache_on_error = true
codexbar_path = "codexbar"
timeout_seconds = 30
```

Provider credentials stay in the upstream CodexBar configuration. This project does not store API keys or browser cookies.

## Local Cost Mode

For Codex on Linux, the most reliable first data source is local cost scanning:

```bash
linux-codex-usage cost --provider codex --format waybar
```

This uses CodexBar's `cost` command to scan local Codex history under `~/.codex`. It does not require browser cookies or WebKit.

Usage-limit mode is still available:

```bash
linux-codex-usage status --provider codex --source cli --format waybar
```

That path depends on the upstream Codex CLI app-server/RPC behavior and may fail when the app-server cannot provide account rate limits.

## Waybar

Add a custom module:

```jsonc
"custom/ai-usage": {
  "exec": "linux-codex-usage cost --provider codex --format waybar",
  "return-type": "json",
  "interval": 60,
  "tooltip": true
}
```

Optional CSS classes:

```css
#custom-ai-usage.ok {
  color: #a6e3a1;
}

#custom-ai-usage.warning {
  color: #f9e2af;
}

#custom-ai-usage.critical,
#custom-ai-usage.error {
  color: #f38ba8;
}

#custom-ai-usage.stale {
  color: #89b4fa;
}
```

## Development Checks

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
python3 -m compileall src tests
```
