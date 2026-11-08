"""Command-line interface for the week-one NetDoctor scaffold."""

from __future__ import annotations

import argparse
import functools
import http.server
import sys
from pathlib import Path
from typing import Sequence

from .config import AppConfig, load_config
from .models import RunResult
from .engine import NetworkEngine
from .analyzer import NetworkAnalyzer


METRIC_PLAN = (
    ("DNS", "호스트 이름을 IP 주소로 변환하는 시간"),
    ("TCP", "미리 확인한 IP 주소와 TCP 연결을 설정하는 시간"),
    ("TTFB", "연결 후 HTTP 요청을 보내 첫 응답 바이트를 받는 시간"),
    ("다운로드", "응답 본문 비트 수를 실제 전송 시간으로 나눈 처리율"),
    ("RTT", "ping 요청이 목적지를 왕복하는 시간과 패킷 손실률"),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netdoctor",
        description="Explainable network quality diagnostics",
    )
    parser.add_argument("--config", help="JSON configuration path")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("plan", help="show the validated measurement plan")
    run_cmd = commands.add_parser("run", help="perform real network measurements and diagnose")
    run_cmd.add_argument("--json", action="store_true", help="emit raw and diagnosis JSON")
    demo = commands.add_parser("demo", help="show fictional data for contract validation")
    demo.add_argument("--json", action="store_true", help="emit the full JSON result")
    dashboard = commands.add_parser("dashboard", help="serve the dashboard wireframe")
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8000)
    return parser


def _print_plan(config: AppConfig) -> None:
    print("NetDoctor 측정 계획 (1주차 설계)")
    print(f"대상: {config.target.name} ({config.target.host}:{config.target.tcp_port})")
    print(f"HTTP: {config.target.http_url}")
    download = config.target.download_url or "미설정 — 허가된 측정 서버 필요"
    print(f"다운로드: {download}")
    print(f"반복: {config.repetitions}회 / 타임아웃: {config.timeout_seconds:g}초")
    print()
    for index, (name, definition) in enumerate(METRIC_PLAN, start=1):
        print(f"{index}. {name}: {definition}")
    print("\n현재 단계에서는 실제 네트워크 요청을 보내지 않습니다.")


def _print_demo(result: RunResult) -> None:
    print("NetDoctor 데모 결과 — 실제 측정값이 아닙니다")
    print(f"대상: {result.target_name} ({result.target_host})")
    for metric in result.metrics:
        assert metric.summary is not None
        summary = metric.summary
        print(
            f"{metric.label:<8} 중앙값 {summary.median:>6.1f} {metric.unit} "
            f"(최소 {summary.minimum:.1f}, 최대 {summary.maximum:.1f})"
        )
    print(f"\n주의: {result.notes[0]}")


def _print_run(result: RunResult) -> None:
    print(f"NetDoctor 실제 네트워크 측정 결과 [{result.started_at[:19]}]")
    print(f"대상: {result.target_name} ({result.target_host}) | 반복: {result.repetitions_requested}회")
    print("-" * 65)
    for metric in result.metrics:
        if metric.status == "success" and metric.summary:
            s = metric.summary
            print(
                f"{metric.label:<10} 중앙값 {s.median:>7.1f} {metric.unit:<4} "
                f"(최소 {s.minimum:>6.1f}, 최대 {s.maximum:>6.1f}, 표준편차 {s.standard_deviation:>5.1f})"
            )
        elif metric.status == "unavailable":
            print(f"{metric.label:<10} [측정 생략] ({metric.error})")
        else:
            print(f"{metric.label:<10} [측정 실패] ({metric.error})")
    print("-" * 65)

    report = NetworkAnalyzer.analyze(result)
    print(f"\n[종합 진단: {report.overall_grade}등급 ({report.overall_score}점)]")
    print(f"상태 요약: {report.headline}")
    print(f"상세 설명: {report.description}")
    if report.bottlenecks:
        print("\n[감지된 병목 지점]")
        for b in report.bottlenecks:
            print(f" • {b}")
    print("\n[서비스별 적합도 예측]")
    for svc in report.services:
        mark = "✓" if svc.suitable else "✗"
        print(f" {mark} {svc.name:<16} {svc.rating_stars} | {svc.summary} ({svc.evidence})")
    print(f"\n주의: {report.uncertainty_note}")


class DashboardRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, default_config: AppConfig, **kwargs):
        self.default_config = default_config
        super().__init__(*args, **kwargs)

    def do_POST(self):
        if self.path == "/api/diagnose":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"
            try:
                import json
                from urllib.parse import urlparse
                from .config import TargetConfig

                payload = json.loads(body) if body else {}
                target_url = payload.get("url", self.default_config.target.http_url)
                reps = int(payload.get("repetitions", self.default_config.repetitions))
                reps = max(5, min(10, reps))

                parsed = urlparse(target_url if "://" in target_url else f"https://{target_url}")
                host = parsed.hostname or self.default_config.target.host
                scheme = parsed.scheme or "https"
                tcp_port = parsed.port or (443 if scheme == "https" else 80)
                http_url = f"{scheme}://{host}:{tcp_port}/" if parsed.port else f"{scheme}://{host}/"

                active_target = TargetConfig(
                    name=payload.get("name", host),
                    host=host,
                    tcp_port=tcp_port,
                    http_url=http_url,
                    download_url=self.default_config.target.download_url,
                )
                active_cfg = AppConfig(
                    target=active_target,
                    repetitions=reps,
                    timeout_seconds=self.default_config.timeout_seconds,
                    pause_between_runs_seconds=self.default_config.pause_between_runs_seconds,
                )

                engine = NetworkEngine(active_cfg)
                run_res = engine.run()
                diag = NetworkAnalyzer.analyze(run_res)

                resp_data = {
                    "run": json.loads(run_res.to_json()),
                    "diagnosis": diag.to_dict(),
                }
                data_bytes = json.dumps(resp_data, ensure_ascii=False).encode("utf-8")

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data_bytes)))
                self.end_headers()
                self.wfile.write(data_bytes)
            except Exception as e:
                err_data = json.dumps({"error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(err_data)))
                self.end_headers()
                self.wfile.write(err_data)
            return

        super().do_POST()


def _serve_dashboard(config: AppConfig, host: str, port: int) -> int:
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    web_root = Path(__file__).resolve().parent / "web"
    handler = functools.partial(
        DashboardRequestHandler,
        directory=str(web_root),
        default_config=config,
    )
    try:
        server = http.server.ThreadingHTTPServer((host, port), handler)
    except OSError as error:
        raise ValueError(f"could not start dashboard server: {error}") from error
    print(f"NetDoctor dashboard: http://{host}:{port}")
    print("종료하려면 Ctrl+C를 누르세요.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nDashboard stopped.")
    finally:
        server.server_close()
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = load_config(args.config)
        if args.command == "plan":
            _print_plan(config)
        elif args.command == "run":
            engine = NetworkEngine(config)
            result = engine.run()
            if args.json:
                report = NetworkAnalyzer.analyze(result)
                import json
                print(json.dumps({
                    "run": json.loads(result.to_json()),
                    "diagnosis": report.to_dict(),
                }, indent=2, ensure_ascii=False))
            else:
                _print_run(result)
        elif args.command == "demo":
            result = RunResult.demo(
                config.target.name,
                config.target.host,
                config.repetitions,
            )
            if args.json:
                print(result.to_json())
            else:
                _print_demo(result)
        elif args.command == "dashboard":
            return _serve_dashboard(config, args.host, args.port)
    except ValueError as error:
        print(f"설정 오류: {error}", file=sys.stderr)
        return 2
    return 0
