"""Explainable diagnosis and rule-based network evaluation engine for Week 3."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

from .models import MetricResult, RunResult


@dataclass(frozen=True, slots=True)
class ServiceEvaluation:
    service_id: str
    name: str
    suitable: bool
    rating_stars: str  # e.g., "★★★★★"
    summary: str
    evidence: str


@dataclass(frozen=True, slots=True)
class DiagnosisReport:
    overall_grade: str  # "최상", "양호", "보통", "주의", "불량"
    overall_score: int  # 0 to 100
    headline: str
    description: str
    bottlenecks: tuple[str, ...]
    services: tuple[ServiceEvaluation, ...]
    uncertainty_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_grade": self.overall_grade,
            "overall_score": self.overall_score,
            "headline": self.headline,
            "description": self.description,
            "bottlenecks": list(self.bottlenecks),
            "services": [asdict(s) for s in self.services],
            "uncertainty_note": self.uncertainty_note,
        }


class NetworkAnalyzer:
    @staticmethod
    def analyze(result: RunResult) -> DiagnosisReport:
        metric_map: dict[str, MetricResult] = {m.key: m for m in result.metrics}

        def get_median(key: str) -> Optional[float]:
            metric = metric_map.get(key)
            if metric and metric.status == "success" and metric.summary:
                return metric.summary.median
            return None

        dns_med = get_median("dns")
        tcp_med = get_median("tcp")
        ttfb_med = get_median("ttfb")
        ping_med = get_median("ping")
        dl_med = get_median("download")

        bottlenecks: list[str] = []

        # 1. 병목 감지 규칙
        if dns_med is not None and dns_med > 80.0:
            bottlenecks.append(f"DNS 응답 지연 (중앙값 {dns_med:.1f}ms): 도메인 네임서버 조회 시간이 깁니다.")
        elif metric_map.get("dns") and metric_map["dns"].status == "failed":
            bottlenecks.append("DNS 조회 실패: 목적지 도메인을 IP로 변환할 수 없습니다.")

        if tcp_med is not None and tcp_med > 120.0:
            bottlenecks.append(f"TCP 연결 설정 지연 (중앙값 {tcp_med:.1f}ms): 3-Way Handshake에 시간이 소요됩니다.")
        elif metric_map.get("tcp") and metric_map["tcp"].status == "failed":
            bottlenecks.append("TCP 연결 실패: 서버 포트에 접근할 수 없거나 방화벽에 차단되었습니다.")

        if ttfb_med is not None and ttfb_med > 300.0:
            bottlenecks.append(f"HTTP TTFB 지연 (중앙값 {ttfb_med:.1f}ms): 웹 서버의 첫 바이트 처리 및 응답 대기 시간이 깁니다.")

        if ping_med is not None and ping_med > 100.0:
            bottlenecks.append(f"높은 왕복 지연시간(RTT) (중앙값 {ping_med:.1f}ms): 원거리 경로이거나 네트워크 링크에 지연이 있습니다.")
        elif metric_map.get("ping") and metric_map["ping"].status == "failed":
            bottlenecks.append("ICMP Ping 실패: 경로상의 방화벽에 의해 ICMP Echo가 차단되었거나 패킷이 손실되었습니다.")

        if dl_med is not None and dl_med < 10.0:
            bottlenecks.append(f"낮은 다운로드 처리율 ({dl_med:.1f} Mbps): 대용량 데이터 전송에 제약이 있습니다.")

        # 2. 서비스별 적합도 판정
        services: list[ServiceEvaluation] = []

        # (1) 웹 브라우징
        dns_ok = metric_map.get("dns") and metric_map["dns"].status == "success" and (dns_med is None or dns_med <= 60.0)
        tcp_ok = metric_map.get("tcp") and metric_map["tcp"].status == "success" and (tcp_med is None or tcp_med <= 80.0)
        ttfb_ok = metric_map.get("ttfb") and metric_map["ttfb"].status == "success" and (ttfb_med is None or ttfb_med <= 250.0)
        web_ok = bool(dns_ok and tcp_ok and ttfb_ok)
        web_stars = "★★★★★" if web_ok else ("★★★☆☆" if len(bottlenecks) <= 2 else "★☆☆☆☆")
        services.append(
            ServiceEvaluation(
                service_id="web",
                name="웹 브라우징",
                suitable=web_ok,
                rating_stars=web_stars,
                summary="DNS와 응답 시작 시간이 안정적입니다." if web_ok else "연결 또는 해석 실패/지연으로 브라우징이 어렵습니다.",
                evidence=f"DNS: {f'{dns_med:.1f}ms' if dns_med is not None else '실패'}, TTFB: {f'{ttfb_med:.1f}ms' if ttfb_med is not None else '실패'}",
            )
        )

        # (2) 1080p FHD 스트리밍
        streaming_1080_ok = bool(
            (dl_med is None or dl_med >= 10.0)
            and (ping_med is not None and ping_med <= 150.0)
            and not (metric_map.get("tcp") and metric_map["tcp"].status == "failed")
        )
        s1080_stars = "★★★★★" if streaming_1080_ok else "★☆☆☆☆"
        services.append(
            ServiceEvaluation(
                service_id="fhd_stream",
                name="1080p 스트리밍",
                suitable=streaming_1080_ok,
                rating_stars=s1080_stars,
                summary="FHD 영상 재생에 충분한 대역폭과 왕복 시간을 유지합니다." if streaming_1080_ok else "연결 불안정 또는 대역폭 부족으로 버퍼링이 발생할 수 있습니다.",
                evidence=f"다운로드: {f'{dl_med:.1f} Mbps' if dl_med is not None else '측정생략'}, RTT: {f'{ping_med:.1f}ms' if ping_med is not None else '실패'}",
            )
        )

        # (3) 4K UHD 스트리밍
        streaming_4k_ok = bool(
            (dl_med is None or dl_med >= 35.0)
            and (ping_med is not None and ping_med <= 100.0)
            and not (metric_map.get("tcp") and metric_map["tcp"].status == "failed")
        )
        s4k_stars = "★★★★★" if streaming_4k_ok else "★☆☆☆☆"
        services.append(
            ServiceEvaluation(
                service_id="uhd_stream",
                name="4K 스트리밍",
                suitable=streaming_4k_ok,
                rating_stars=s4k_stars,
                summary="고화질 4K 콘텐츠를 버퍼링 없이 감상하기에 적합합니다." if streaming_4k_ok else "4K 고대역폭 요구조건을 충족하기 어렵습니다.",
                evidence=f"다운로드: {f'{dl_med:.1f} Mbps' if dl_med is not None else '측정생략'}",
            )
        )

        # (4) 실시간 화상회의 / 음성 통화
        conf_ok = (ping_med is None or ping_med <= 60.0) and (
            metric_map.get("ping") and metric_map["ping"].status == "success"
        )
        conf_stars = "★★★★★" if conf_ok else ("★★★☆☆" if (ping_med and ping_med <= 120.0) else "★☆☆☆☆")
        services.append(
            ServiceEvaluation(
                service_id="conference",
                name="화상회의 / 보이스톡",
                suitable=conf_ok,
                rating_stars=conf_stars,
                summary="RTT가 낮고 지연이 적어 오디오/비디오 싱크가 자연스럽습니다." if conf_ok else "음성 딜레이 또는 화면 끊김이 느껴질 수 있습니다.",
                evidence=f"RTT: {ping_med or 0:.1f}ms (권장 60ms 이하)",
            )
        )

        # 3. 종합 평가 및 점수
        if not bottlenecks:
            grade = "최상"
            score = 95
            headline = "뚜렷한 병목이 보이지 않는 쾌적한 상태입니다."
            desc = "주요 지표가 권장 범위 내에 있어 일반 웹 서핑, 고화질 영상, 실시간 화상회의 모두 원활합니다."
        elif len(bottlenecks) == 1:
            grade = "양호"
            score = 80
            headline = "전반적으로 양호하나 경미한 지연 요소가 있습니다."
            desc = bottlenecks[0]
        elif len(bottlenecks) == 2:
            grade = "주의"
            score = 65
            headline = "일부 구간에 병목 현상이 감지되었습니다."
            desc = " ".join(bottlenecks)
        else:
            grade = "불량"
            score = 45
            headline = "복합적인 네트워크 성능 저하가 발생하고 있습니다."
            desc = " ".join(bottlenecks)

        uncertainty = (
            f"본 진단은 최근 {result.repetitions_requested}회의 표본을 바탕으로 한 판정이며, "
            "주변 Wi-Fi 전파 간섭, 공유기 순간 부하, 원격 서버 트래픽 상황에 따라 달라질 수 있습니다."
        )

        return DiagnosisReport(
            overall_grade=grade,
            overall_score=score,
            headline=headline,
            description=desc,
            bottlenecks=tuple(bottlenecks),
            services=tuple(services),
            uncertainty_note=uncertainty,
        )
