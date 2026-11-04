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


def _serve_dashboard(host: str, port: int) -> int:
    if not 1 <= port <= 65535:
        raise ValueError("port must be between 1 and 65535")
    web_root = Path(__file__).resolve().parent / "web"
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(web_root))
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
            return _serve_dashboard(args.host, args.port)
    except ValueError as error:
        print(f"설정 오류: {error}", file=sys.stderr)
        return 2
    return 0
