"""Network measurement engine implementing Week 2 requirements.

Measures DNS lookup, TCP connect, HTTP TTFB, download throughput, and ICMP Ping RTT.
Robustly isolates failures so that a failure in one metric does not crash the pipeline.
"""

from __future__ import annotations

import math
import platform
import re
import socket
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Optional
from uuid import uuid4

from .config import AppConfig
from .models import MetricResult, MetricStatus, RunResult


class NetworkEngine:
    def __init__(self, config: AppConfig):
        self.config = config
        self.target = config.target
        self.repetitions = config.repetitions
        self.timeout = config.timeout_seconds
        self.pause = config.pause_between_runs_seconds

    def measure_dns_once(self) -> float:
        """Resolve host to IP and measure elapsed time in milliseconds."""
        start = time.perf_counter()
        # socket.getaddrinfo performs the DNS query
        addrinfo = socket.getaddrinfo(
            self.target.host,
            self.target.tcp_port,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        if not addrinfo:
            raise RuntimeError("DNS resolution returned no addresses")
        return elapsed_ms

    def resolve_target_ip(self) -> str:
        """Helper to get target IPv4 address for TCP connect tests."""
        addrinfo = socket.getaddrinfo(
            self.target.host,
            self.target.tcp_port,
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
        )
        return addrinfo[0][4][0]

    def measure_tcp_once(self, ip: str) -> float:
        """Measure 3-way handshake time to target IP in milliseconds."""
        start = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((ip, self.target.tcp_port))
            return (time.perf_counter() - start) * 1000.0
        finally:
            sock.close()

    def measure_ttfb_once(self) -> float:
        """Measure Time To First Byte (TTFB) in milliseconds."""
        req = urllib.request.Request(
            self.target.http_url,
            headers={"User-Agent": "NetDoctor/2.0"},
        )
        start = time.perf_counter()
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            # Read 1 byte to ensure response headers and first byte arrived
            _ = resp.read(1)
            return (time.perf_counter() - start) * 1000.0

    def measure_throughput_once(self) -> float:
        """Measure download throughput in Mbps using target.download_url."""
        if not self.target.download_url:
            raise RuntimeError("Download URL is not configured")

        req = urllib.request.Request(
            self.target.download_url,
            headers={"User-Agent": "NetDoctor/2.0"},
        )
        start = time.perf_counter()
        total_bytes = 0
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                total_bytes += len(chunk)

        elapsed = time.perf_counter() - start
        if elapsed <= 0 or total_bytes == 0:
            raise RuntimeError("No bytes downloaded")
        # Throughput in Mbps: (bytes * 8) / (seconds * 1,000,000)
        return (total_bytes * 8) / (elapsed * 1_000_000.0)

    def measure_ping_once(self) -> float:
        """Measure 1-hop ICMP ping RTT in milliseconds."""
        is_win = platform.system().lower() == "windows"
        count_flag = "-n" if is_win else "-c"
        timeout_ms = int(self.timeout * 1000)

        if is_win:
            cmd = ["ping", count_flag, "1", "-w", str(timeout_ms), self.target.host]
        else:
            # On Linux/macOS, -W is in seconds
            cmd = ["ping", count_flag, "1", "-W", str(max(1, int(self.timeout))), self.target.host]

        start = time.perf_counter()
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000.0

        if res.returncode != 0:
            raise RuntimeError("ICMP ping packet lost or blocked")

        # Parse output for precise ping time if possible
        # Windows: "시간=12ms" or "time=12ms" or "time<1ms"
        # Linux: "time=12.3 ms"
        match = re.search(r"(?:time|시간)[=<]([0-9.]+)\s*ms", res.stdout, re.IGNORECASE)
        if match:
            return float(match.group(1))
        return elapsed_ms

    def _repeat_metric(
        self,
        key: str,
        label: str,
        unit: str,
        measure_func: Callable[[], float],
    ) -> MetricResult:
        """Execute a measurement function N times with error isolation."""
        samples: list[float] = []
        last_error: Optional[str] = None

        for idx in range(self.repetitions):
            if idx > 0 and self.pause > 0:
                time.sleep(self.pause)
            try:
                val = measure_func()
                samples.append(val)
            except Exception as e:
                last_error = str(e)

        if samples:
            return MetricResult(
                key=key,
                label=label,
                unit=unit,
                samples=tuple(samples),
                status="success",
            )
        else:
            # If unavailable (e.g. download_url null), status is unavailable
            status: MetricStatus = "unavailable" if "not configured" in (last_error or "") else "failed"
            return MetricResult(
                key=key,
                label=label,
                unit=unit,
                samples=(),
                status=status,
                error=last_error or "All attempts failed",
            )

    def run(self) -> RunResult:
        """Run the complete measurement suite."""
        started_at = datetime.now(timezone.utc).isoformat()
        metrics: list[MetricResult] = []

        # 1. DNS Measurement
        dns_result = self._repeat_metric("dns", "DNS", "ms", self.measure_dns_once)
        metrics.append(dns_result)

        # 2. TCP Measurement (resolve IP first to isolate TCP connect time from DNS)
        try:
            target_ip = self.resolve_target_ip()
            tcp_result = self._repeat_metric("tcp", "TCP 연결", "ms", lambda: self.measure_tcp_once(target_ip))
        except Exception as e:
            tcp_result = MetricResult(
                key="tcp",
                label="TCP 연결",
                unit="ms",
                samples=(),
                status="failed",
                error=f"Cannot resolve IP for TCP test: {e}",
            )
        metrics.append(tcp_result)

        # 3. TTFB Measurement
        ttfb_result = self._repeat_metric("ttfb", "TTFB", "ms", self.measure_ttfb_once)
        metrics.append(ttfb_result)

        # 4. Ping (RTT) Measurement
        ping_result = self._repeat_metric("ping", "RTT", "ms", self.measure_ping_once)
        metrics.append(ping_result)

        # 5. Throughput Download Measurement
        download_result = self._repeat_metric("download", "다운로드", "Mbps", self.measure_throughput_once)
        metrics.append(download_result)

        finished_at = datetime.now(timezone.utc).isoformat()

        notes = [
            f"실제 측정 수행 완료 (반복 {self.repetitions}회).",
            "측정 지표는 네트워크 변동에 따라 매 회차마다 달라질 수 있습니다.",
        ]

        return RunResult(
            schema_version="1.0",
            run_id=str(uuid4()),
            mode="measured",
            target_name=self.target.name,
            target_host=self.target.host,
            repetitions_requested=self.repetitions,
            started_at=started_at,
            finished_at=finished_at,
            metrics=tuple(metrics),
            notes=tuple(notes),
        )
