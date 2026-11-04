import json
import unittest

from netdoctor.models import MetricResult, RunResult, StatisticalSummary


class StatisticalSummaryTests(unittest.TestCase):
    def test_summary_contains_required_statistics(self) -> None:
        summary = StatisticalSummary.from_samples([10, 20, 30, 40, 100])
        self.assertEqual(summary.count, 5)
        self.assertEqual(summary.mean, 40)
        self.assertEqual(summary.median, 30)
        self.assertEqual(summary.minimum, 10)
        self.assertEqual(summary.maximum, 100)
        self.assertGreater(summary.standard_deviation, 0)

    def test_empty_and_negative_samples_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least one"):
            StatisticalSummary.from_samples([])
        with self.assertRaisesRegex(ValueError, "non-negative"):
            StatisticalSummary.from_samples([1, -1])


class ResultContractTests(unittest.TestCase):
    def test_success_requires_samples(self) -> None:
        with self.assertRaisesRegex(ValueError, "must contain samples"):
            MetricResult("dns_ms", "DNS", "ms", ())

    def test_failed_result_requires_error_and_has_no_summary(self) -> None:
        metric = MetricResult(
            "rtt_ms",
            "RTT",
            "ms",
            (),
            status="failed",
            error="ICMP unavailable",
        )
        self.assertIsNone(metric.summary)

    def test_demo_json_is_explicit_and_serializable(self) -> None:
        result = RunResult.demo("Example", "example.com", 7)
        payload = json.loads(result.to_json())
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertEqual(payload["mode"], "demo")
        self.assertEqual(len(payload["metrics"]), 5)
        self.assertTrue(all(len(metric["samples"]) == 7 for metric in payload["metrics"]))
        self.assertIn("실제 측정 결과가 아닙니다", payload["notes"][0])


if __name__ == "__main__":
    unittest.main()
