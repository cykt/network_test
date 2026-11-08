"""Extended regression and scenario tests for the full NetDoctor pipeline."""

import unittest
from netdoctor.config import AppConfig, TargetConfig
from netdoctor.engine import NetworkEngine
from netdoctor.analyzer import NetworkAnalyzer
from netdoctor.models import MetricResult, RunResult, StatisticalSummary


class FullPipelineTests(unittest.TestCase):
    def setUp(self):
        self.target = TargetConfig(
            name="Test Local Target",
            host="127.0.0.1",
            tcp_port=80,
            http_url="http://127.0.0.1:80/",
            download_url=None,
        )
        self.config = AppConfig(
            target=self.target,
            repetitions=5,
            timeout_seconds=0.5,
            pause_between_runs_seconds=0.0,
        )

    def test_analyzer_with_fictional_healthy_data(self):
        """Healthy network data should result in '최상' or '양호' rating and full stars."""
        demo_res = RunResult.demo("Healthy", "127.0.0.1", 5)
        report = NetworkAnalyzer.analyze(demo_res)
        self.assertIn(report.overall_grade, ["최상", "양호"])
        self.assertGreaterEqual(report.overall_score, 80)
        self.assertEqual(len(report.services), 4)

    def test_analyzer_with_failures(self):
        """Failed metrics should not crash analyzer and must show up in bottlenecks."""
        metrics = (
            MetricResult("dns", "DNS", "ms", (), status="failed", error="DNS timeout"),
            MetricResult("tcp", "TCP 연결", "ms", (), status="failed", error="Connection refused"),
            MetricResult("ttfb", "TTFB", "ms", (), status="failed", error="No response"),
            MetricResult("ping", "RTT", "ms", (), status="failed", error="Ping timeout"),
            MetricResult("download", "다운로드", "Mbps", (), status="unavailable", error="Not configured"),
        )
        run_res = RunResult(
            schema_version="1.0",
            run_id="test-fail",
            mode="measured",
            target_name="Failed Target",
            target_host="invalid.local",
            repetitions_requested=5,
            started_at="2026-11-08T00:00:00Z",
            finished_at="2026-11-08T00:00:01Z",
            metrics=metrics,
        )
        report = NetworkAnalyzer.analyze(run_res)
        self.assertEqual(report.overall_grade, "불량")
        self.assertLessEqual(report.overall_score, 50)
        self.assertGreater(len(report.bottlenecks), 0)

    def test_engine_graceful_handling_invalid_host(self):
        """Engine should handle completely non-existent host without unhandled exception."""
        bad_target = TargetConfig(
            name="Non-existent",
            host="this-domain-does-not-exist-at-all-12345.xyz",
            tcp_port=80,
            http_url="http://this-domain-does-not-exist-at-all-12345.xyz/",
            download_url=None,
        )
        bad_config = AppConfig(
            target=bad_target,
            repetitions=5,
            timeout_seconds=0.5,
            pause_between_runs_seconds=0.0,
        )
        engine = NetworkEngine(bad_config)
        res = engine.run()
        self.assertEqual(len(res.metrics), 5)
        self.assertEqual(res.metrics[0].status, "failed")
        self.assertIn("failed", res.metrics[0].error.lower())
