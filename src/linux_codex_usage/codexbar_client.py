from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any


class CodexBarError(RuntimeError):
    """Raised when the external codexbar command cannot return valid data."""


@dataclass(slots=True)
class CodexBarClient:
    executable: str = "codexbar"
    timeout_seconds: int = 30

    def fetch_json(self, providers: list[str] | None = None) -> Any:
        command = self._build_command(providers)

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise CodexBarError(
                f"codexbar executable not found: {self.executable}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise CodexBarError(
                f"codexbar command timed out after {self.timeout_seconds}s"
            ) from exc

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            stdout = completed.stdout.strip()
            detail = stderr or stdout or f"exit code {completed.returncode}"
            raise CodexBarError(f"codexbar command failed: {detail}")

        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise CodexBarError("codexbar returned invalid JSON") from exc

    def _build_command(self, providers: list[str] | None) -> list[str]:
        selected = providers or ["all"]
        command = [self.executable, "--format", "json"]
        for provider in selected:
            command.extend(["--provider", provider])
        return command

