import unittest
from unittest.mock import patch

from click.testing import CliRunner

from harvester import main


class TestCliPresets(unittest.TestCase):
    def test_webtoon_preset_applies_crawl_defaults(self):
        captured = {}

        def fake_process(**kwargs):
            captured.update(kwargs)

        runner = CliRunner()
        with patch("harvester.process_single_url", side_effect=fake_process):
            result = runner.invoke(main, ["--webtoon", "https://example.com", "-y", "--dry-run"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(captured["depth"], 1)
        self.assertEqual(captured["link_pattern"], r"viewer")
        self.assertEqual(captured["media_type_filter"], "images")
        self.assertGreaterEqual(captured["min_height"], 800)


if __name__ == "__main__":
    unittest.main()
