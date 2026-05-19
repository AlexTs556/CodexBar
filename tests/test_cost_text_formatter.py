import unittest

from linux_codex_usage.formatters.cost_text_formatter import format_cost_text
from linux_codex_usage.normalize import normalize_usage


class CostTextFormatterTest(unittest.TestCase):
    def test_formats_cost_summary(self):
        report = normalize_usage(
            [
                {
                    "provider": "codex",
                    "source": "local",
                    "updatedAt": "2026-05-19T20:51:18Z",
                    "last30DaysCostUSD": 15.75,
                    "last30DaysTokens": 3000000,
                    "daily": [
                        {
                            "date": "2026-05-18",
                            "totalCost": 5.25,
                            "totalTokens": 1000000,
                            "modelsUsed": ["gpt-5.4"],
                            "modelBreakdowns": [
                                {
                                    "modelName": "gpt-5.4",
                                    "cost": 5.25,
                                    "totalTokens": 1000000,
                                }
                            ],
                        },
                        {
                            "date": "2026-05-19",
                            "totalCost": 10.5,
                            "totalTokens": 2000000,
                            "modelsUsed": ["gpt-5.5"],
                            "modelBreakdowns": [
                                {
                                    "modelName": "gpt-5.5",
                                    "cost": 10.5,
                                    "totalTokens": 2000000,
                                }
                            ],
                        },
                    ],
                }
            ]
        )

        text = format_cost_text(report)

        self.assertIn("Codex cost summary", text)
        self.assertIn("Today:      $10.50 / 2.00M tokens", text)
        self.assertIn("Last 30d:   $15.75 / 3.00M tokens", text)
        self.assertIn("gpt-5.5", text)
        self.assertIn("2026-05-19", text)


if __name__ == "__main__":
    unittest.main()
