import json
import unittest

from linux_codex_usage.formatters.waybar_formatter import format_waybar
from linux_codex_usage.models import ProviderUsage, UsageReport, WindowUsage


class WaybarFormatterTest(unittest.TestCase):
    def test_formats_ok_payload(self):
        report = UsageReport(
            providers=[
                ProviderUsage(
                    provider="codex",
                    label="Codex",
                    windows=[
                        WindowUsage(
                            name="session",
                            used_percent=28,
                            remaining_percent=72,
                            reset_label="2h 15m",
                        )
                    ],
                )
            ]
        )

        payload = json.loads(format_waybar(report))

        self.assertEqual(payload["text"], "Codex session 28%")
        self.assertEqual(payload["class"], "ok")
        self.assertIn("2h 15m", payload["tooltip"])

    def test_marks_critical_threshold(self):
        report = UsageReport(
            providers=[
                ProviderUsage(
                    provider="codex",
                    label="Codex",
                    windows=[WindowUsage(name="weekly", used_percent=96)],
                )
            ]
        )

        payload = json.loads(format_waybar(report, critical_threshold=95))

        self.assertEqual(payload["class"], "critical")

    def test_keeps_error_output_valid_json(self):
        report = UsageReport(providers=[], error="codexbar executable not found")

        payload = json.loads(format_waybar(report))

        self.assertEqual(payload["class"], "error")
        self.assertEqual(payload["text"], "AI usage unavailable")


if __name__ == "__main__":
    unittest.main()
