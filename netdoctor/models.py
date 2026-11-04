"""Stable result models shared by future measurers, analyzers, and the API."""

from __future__ import annotations

import json
import math
import statistics
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Literal
from uuid import uuid4


MetricStatus = Literal["success", "unavailable", "failed"]


@dataclass(frozen=True, slots=True)
class StatisticalSummary:
    count: int
    mean: float
    median: float
    minimum: float
    maximum: float
    standard_deviation: float

    @classmethod
    def from_samples(cls, samples: Iterable[float]) -> StatisticalSummary:
        values = [float(sample) for sample in samples]
        if not values:
            raise ValueError("at least one sample is required")
        if any(not math.isfinite(value) or value < 0 for value in values):
            raise ValueError("samples must be finite, non-negative numbers")
        return cls(
            count=len(values),
            mean=statistics.fmean(values),
            median=statistics.median(values),
            minimum=min(values),
            maximum=max(values),
            standard_deviation=statistics.pstdev(values),
        )


@dataclass(frozen=True, slots=True)
class MetricResult:
    key: str
    label: str
    unit: str
    samples: tuple[float, ...]
    status: MetricStatus = "success"
    error: str | None = None
    summary: StatisticalSummary | None = field(init=False)

    def __post_init__(self) -> None:
        if self.status not in {"success", "unavailable", "failed"}:
            raise ValueError(f"unsupported metric status: {self.status}")
        if self.status == "success" and not self.samples:
            raise ValueError("a successful metric must contain samples")
        if self.status != "success" and self.samples:
            raise ValueError("an unsuccessful metric cannot contain samples")
        if self.status == "failed" and not self.error:
            raise ValueError("a failed metric must contain an error message")
        if self.status == "success" and self.error:
            raise ValueError("a successful metric cannot contain an error message")
        summary = StatisticalSummary.from_samples(self.samples) if self.samples else None
        object.__setattr__(self, "summary", summary)


@dataclass(frozen=True, slots=True)
class RunResult:
    schema_version: str
    run_id: str
    mode: Literal["demo", "measured"]
    target_name: str
    target_host: str
    repetitions_requested: int
    started_at: str
    finished_at: str
    metrics: tuple[MetricResult, ...]
    notes: tuple[str, ...] = ()

    @classmethod
    def demo(cls, target_name: str, target_host: str, repetitions: int) -> RunResult:
        """Create deterministic fictional data for validating the week-one contract."""

        if not 5 <= repetitions <= 10:
            raise ValueError("demo repetitions must be between 5 and 10")

        def fit(values: tuple[float, ...]) -> tuple[float, ...]:
            return tuple(values[index % len(values)] for index in range(repetitions))

        now = datetime.now(timezone.utc).isoformat()
        return cls(
            schema_version="1.0",
            run_id=str(uuid4()),
            mode="demo",
            target_name=target_name,
            target_host=target_host,
            repetitions_requested=repetitions,
            started_at=now,
            finished_at=now,
            metrics=(
                MetricResult("dns_ms", "DNS", "ms", fit((11.8, 12.4, 12.0, 13.1, 12.2))),
                MetricResult(
                    "tcp_ms", "TCP 연결", "ms", fit((20.2, 21.0, 20.8, 22.1, 20.5))
                ),
                MetricResult(
                    "ttfb_ms", "TTFB", "ms", fit((69.2, 72.4, 71.8, 75.1, 70.7))
                ),
                MetricResult("rtt_ms", "RTT", "ms", fit((17.5, 18.2, 18.0, 19.1, 17.8))),
                MetricResult(
                    "download_mbps",
                    "다운로드",
                    "Mbps",
                    fit((70.2, 72.1, 71.5, 73.0, 72.4)),
                ),
            ),
            notes=("이 값은 UI와 데이터 계약 확인용 예시이며 실제 측정 결과가 아닙니다.",),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)
