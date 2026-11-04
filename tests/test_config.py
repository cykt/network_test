import json
import tempfile
import unittest
from pathlib import Path

from netdoctor.config import AppConfig, TargetConfig, load_config


class ConfigTests(unittest.TestCase):
    def test_default_config_is_valid(self) -> None:
        config = load_config()
        self.assertEqual(config.repetitions, 5)
        self.assertEqual(config.target.host, "example.com")
        self.assertIsNone(config.target.download_url)

    def test_repetitions_must_be_between_five_and_ten(self) -> None:
        target = TargetConfig("target", "example.com", 443, "https://example.com")
        with self.assertRaisesRegex(ValueError, "between 5 and 10"):
            AppConfig(4, 5.0, 0.25, target)
        with self.assertRaisesRegex(ValueError, "between 5 and 10"):
            AppConfig(11, 5.0, 0.25, target)

    def test_urls_must_be_absolute_http_urls(self) -> None:
        with self.assertRaisesRegex(ValueError, "absolute http"):
            TargetConfig("target", "example.com", 443, "/relative")

    def test_missing_field_has_readable_error(self) -> None:
        values = {"repetitions": 5}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(values), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing configuration field"):
                load_config(path)


if __name__ == "__main__":
    unittest.main()
