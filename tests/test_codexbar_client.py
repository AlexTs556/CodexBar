import unittest
from unittest.mock import patch

from subprocess import CompletedProcess

from linux_codex_usage.codexbar_client import CodexBarClient


class CodexBarClientTest(unittest.TestCase):
    def test_builds_usage_json_command(self):
        client = CodexBarClient("codexbar")

        command = client._build_command(["codex", "claude"], source="cli")

        self.assertEqual(
            command,
            [
                "codexbar",
                "usage",
                "--format",
                "json",
                "--provider",
                "codex",
                "--provider",
                "claude",
                "--source",
                "cli",
            ],
        )

    def test_returns_json_stdout_when_command_exits_nonzero(self):
        client = CodexBarClient("codexbar")

        with patch("linux_codex_usage.codexbar_client.subprocess.run") as run:
            run.return_value = CompletedProcess(
                args=[],
                returncode=1,
                stdout='[{"provider":"synthetic","error":{"message":"failed"}}]',
                stderr="",
            )

            data = client.fetch_json(["synthetic"])

        self.assertEqual(data[0]["provider"], "synthetic")


if __name__ == "__main__":
    unittest.main()
