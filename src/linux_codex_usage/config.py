from __future__ import annotations

import os
import shutil
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def default_config_path() -> Path:
    config_home = os.environ.get("XDG_CONFIG_HOME")
    base = Path(config_home) if config_home else Path.home() / ".config"
    return base / "linux-codex-usage" / "config.toml"


@dataclass(slots=True)
class AppConfig:
    providers: list[str] = field(default_factory=lambda: ["all"])
    warning_threshold: float = 80.0
    critical_threshold: float = 95.0
    use_cache_on_error: bool = True
    codexbar_path: str = "codexbar"
    timeout_seconds: int = 30

    @classmethod
    def load(cls, path: Path | None = None) -> "AppConfig":
        config_path = path or default_config_path()
        if not config_path.exists():
            return cls()

        data = tomllib.loads(config_path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        providers = data.get("providers", ["all"])
        if isinstance(providers, str):
            providers = [providers]
        if not isinstance(providers, list):
            providers = ["all"]

        return cls(
            providers=[str(provider) for provider in providers],
            warning_threshold=_float_value(data.get("warning_threshold"), 80.0),
            critical_threshold=_float_value(data.get("critical_threshold"), 95.0),
            use_cache_on_error=bool(data.get("use_cache_on_error", True)),
            codexbar_path=str(data.get("codexbar_path") or "codexbar"),
            timeout_seconds=int(_float_value(data.get("timeout_seconds"), 30.0)),
        )

    def to_toml(self) -> str:
        providers = ", ".join(f'"{provider}"' for provider in self.providers)
        return "\n".join(
            [
                f"providers = [{providers}]",
                f"warning_threshold = {self.warning_threshold:g}",
                f"critical_threshold = {self.critical_threshold:g}",
                f"use_cache_on_error = {str(self.use_cache_on_error).lower()}",
                f'codexbar_path = "{self.codexbar_path}"',
                f"timeout_seconds = {self.timeout_seconds}",
                "",
            ]
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "providers": self.providers,
            "warning_threshold": self.warning_threshold,
            "critical_threshold": self.critical_threshold,
            "use_cache_on_error": self.use_cache_on_error,
            "codexbar_path": self.codexbar_path,
            "timeout_seconds": self.timeout_seconds,
        }


def create_default_config(path: Path | None = None) -> Path:
    config_path = path or default_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        config_path.write_text(AppConfig().to_toml(), encoding="utf-8")
    return config_path


def resolve_codexbar_path(cli_value: str | None, config: AppConfig) -> str:
    for candidate in _codexbar_candidates(cli_value, config):
        if _is_executable(candidate):
            return candidate

    return cli_value or config.codexbar_path or "codexbar"


def _codexbar_candidates(cli_value: str | None, config: AppConfig) -> list[str]:
    candidates: list[str] = []
    if cli_value:
        candidates.append(cli_value)
    if config.codexbar_path:
        candidates.append(config.codexbar_path)

    repo_root = Path(__file__).resolve().parents[2]
    candidates.append(str(repo_root / "tools" / "codexbar-cli" / "codexbar"))
    candidates.append("codexbar")
    return candidates


def _is_executable(candidate: str) -> bool:
    path = Path(candidate).expanduser()
    if path.is_file() and os.access(path, os.X_OK):
        return True
    return shutil.which(candidate) is not None


def _float_value(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
