import unittest
import json
from pathlib import Path

from linux_codex_usage.normalize import normalize_usage


class NormalizeUsageTest(unittest.TestCase):
    def test_normalizes_provider_list(self):
        report = normalize_usage(
            {
                "providers": [
                    {
                        "provider": "codex",
                        "label": "Codex",
                        "source": "codex-cli",
                        "account": "user@example.com",
                        "windows": [
                            {
                                "name": "session",
                                "used_percent": 28,
                                "resets_at": "2026-05-19T21:15:00Z",
                            }
                        ],
                        "credits": {"remaining": 112.4, "unit": "credits"},
                    }
                ]
            }
        )

        provider = report.providers[0]
        self.assertEqual(provider.provider, "codex")
        self.assertEqual(provider.label, "Codex")
        self.assertEqual(provider.account, "user@example.com")
        self.assertEqual(provider.windows[0].remaining_percent, 72.0)
        self.assertEqual(provider.credits.remaining, 112.4)

    def test_normalizes_provider_map(self):
        report = normalize_usage(
            {
                "codex": {
                    "source": "codex-cli",
                    "limits": {
                        "weekly": {
                            "remaining_percent": "41%",
                            "reset_label": "Fri 09:00",
                        }
                    },
                }
            }
        )

        provider = report.providers[0]
        self.assertEqual(provider.provider, "codex")
        self.assertEqual(provider.label, "Codex")
        self.assertEqual(provider.windows[0].name, "weekly")
        self.assertEqual(provider.windows[0].used_percent, 59.0)

    def test_normalizes_single_provider(self):
        report = normalize_usage(
            {
                "provider": "openai",
                "remaining": 12.5,
                "unit": "usd",
            }
        )

        provider = report.providers[0]
        self.assertEqual(provider.provider, "openai")
        self.assertEqual(provider.credits.remaining, 12.5)
        self.assertEqual(provider.credits.unit, "usd")

    def test_normalizes_fixture(self):
        fixture = Path(__file__).parent / "fixtures" / "codexbar_usage.json"
        report = normalize_usage(json.loads(fixture.read_text(encoding="utf-8")))

        self.assertEqual(report.providers[0].provider, "codex")
        self.assertEqual(len(report.providers[0].windows), 2)

    def test_normalizes_nested_provider_error(self):
        report = normalize_usage(
            [
                {
                    "provider": "synthetic",
                    "source": "auto",
                    "error": {
                        "message": "No available fetch strategy for synthetic.",
                        "code": 1,
                    },
                }
            ]
        )

        provider = report.providers[0]
        self.assertEqual(provider.status, "error")
        self.assertEqual(provider.error, "No available fetch strategy for synthetic.")

    def test_normalizes_cost_payload(self):
        report = normalize_usage(
            [
                {
                    "provider": "codex",
                    "source": "local",
                    "last30DaysCostUSD": 123.45,
                    "sessionCostUSD": 6.78,
                    "updatedAt": "2026-05-19T20:51:18Z",
                }
            ]
        )

        provider = report.providers[0]
        self.assertEqual(provider.source, "local")
        self.assertEqual(provider.updated_at, "2026-05-19T20:51:18Z")
        self.assertEqual(provider.credits.used, 123.45)
        self.assertEqual(provider.credits.unit, "USD")


if __name__ == "__main__":
    unittest.main()
