import tempfile
import unittest
from pathlib import Path

from linux_codex_usage.cache import UsageCache
from linux_codex_usage.models import ProviderUsage, UsageReport, WindowUsage


class UsageCacheTest(unittest.TestCase):
    def test_round_trips_report(self):
        with tempfile.TemporaryDirectory() as directory:
            cache = UsageCache(Path(directory) / "status.json")
            cache.save(
                UsageReport(
                    providers=[
                        ProviderUsage(
                            provider="codex",
                            label="Codex",
                            windows=[
                                WindowUsage(
                                    name="session",
                                    used_percent=28,
                                    remaining_percent=72,
                                )
                            ],
                        )
                    ]
                )
            )

            report = cache.load()

        self.assertIsNotNone(report)
        self.assertEqual(report.providers[0].provider, "codex")
        self.assertEqual(report.providers[0].windows[0].remaining_percent, 72)


if __name__ == "__main__":
    unittest.main()

