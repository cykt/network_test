import contextlib
import io
import json
import unittest

from netdoctor.cli import main


class CliTests(unittest.TestCase):
    def test_plan_describes_all_metrics_without_measuring(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["plan"])
        text = output.getvalue()
        self.assertEqual(exit_code, 0)
        for label in ("DNS", "TCP", "TTFB", "다운로드", "RTT"):
            self.assertIn(label, text)
        self.assertIn("실제 네트워크 요청을 보내지 않습니다", text)

    def test_demo_json_is_valid(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["demo", "--json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["mode"], "demo")


if __name__ == "__main__":
    unittest.main()
