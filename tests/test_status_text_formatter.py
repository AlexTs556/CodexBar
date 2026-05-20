import unittest

from linux_codex_usage.formatters.text_formatter import format_text
from linux_codex_usage.normalize import normalize_usage


class StatusTextFormatterTest(unittest.TestCase):
    def test_formats_live_windows(self):
        report = normalize_usage(
            [
                {
                    "provider": "codex",
                    "source": "oauth",
                    "usage": {
                        "accountEmail": "user@example.com",
                        "primary": {
                            "resetDescription": "10:37 PM",
                            "usedPercent": 0,
                            "windowMinutes": 300,
                        },
                        "secondary": {
                            "resetDescription": "26 May 2026 at 8:42 PM",
                            "usedPercent": 4,
                            "windowMinutes": 10080,
                        },
                    },
                }
            ]
        )

        text = format_text(report)

        self.assertIn("user@example.com", text)
        self.assertIn("5h", text)
        self.assertIn("weekly", text)
        self.assertIn("100%", text)


if __name__ == "__main__":
    unittest.main()
