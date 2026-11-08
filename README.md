# NetDoctor

NetDoctor는 DNS 조회, TCP 연결, HTTP 응답 시작 시간(TTFB), 다운로드 처리율,
RTT를 측정하고, 측정 결과를 바탕으로 네트워크 상태와 가능한 원인을 설명하는
네트워크 품질 진단 프로젝트입니다.

## 현재 구현 상태

현재 저장소에는 1차 실행 가능한 백엔드 골격과 핵심 측정·진단 기능이 구현되어
있습니다. 기존의 설계·데모 단계에서 실제 측정과 규칙 기반 분석 단계로 확장된
상태입니다.

### 구현 완료 또는 기본 동작 확인

- [x] Python 패키지 및 실행 구조
- [x] 측정 대상·반복 횟수·타임아웃 설정 및 검증
- [x] DNS 조회 시간 측정
- [x] TCP 연결 시간 측정
- [x] HTTP TTFB 측정
- [x] 다운로드 처리율 측정
- [x] ICMP Ping RTT 측정
- [x] 반복 측정 및 중앙값·평균·최솟값·최댓값·표준편차 요약
- [x] 측정 실패·타임아웃·부분 실패 격리
- [x] JSON 결과 출력
- [x] 규칙 기반 병목 분석 및 종합 등급 산출
- [x] 웹 브라우징·1080p·4K·화상회의 적합도 평가 기본 구조
- [x] CLI 실행 및 `/api/diagnose` 측정 API 기본 구조
- [x] 정상·실패·비정상 입력에 대한 기본 테스트
- [x] 기본 웹 화면 및 실행 안내 구조

### 앞으로 보완할 항목

- [ ] Windows·macOS·Linux별 ping 출력 파싱 검증
- [ ] DNS·TCP·TLS·TTFB 측정 범위의 명확한 분리와 문서화
- [ ] 패킷 손실률·지터 계산 및 표시 보완
- [ ] 임계값·서비스별 별점 기준의 실측 기반 튜닝
- [ ] Upstage Solar Tool Calling 에이전트(`agent.py`) 연동
- [ ] 측정 JSON을 활용한 자연어 질의응답
- [ ] 완성형 반응형 대시보드, 진행 표시, Chart.js 그래프
- [ ] 이전 측정 결과 비교 기능
- [ ] 브라우저 진단부터 결과 표시까지 E2E 테스트
- [ ] 유선·Wi-Fi·부하·필요 시 모바일 테더링 환경 비교 실험
- [ ] README·실험표·최종 보고서·발표 자료 최신화

## 빠른 시작

Python 3.11 이상이 필요합니다.

```powershell
python -m netdoctor plan
python -m netdoctor run
python -m netdoctor run --json
python -m netdoctor dashboard --port 8000
```

`dashboard` 실행 후 <http://127.0.0.1:8000>을 엽니다. 종료할 때는 `Ctrl+C`를
누릅니다.

설치형 명령을 사용하려면 다음과 같이 개발 모드로 설치합니다.

```powershell
python -m pip install -e .
netdoctor plan
```

## 테스트

```powershell
python -m unittest discover -s tests -v
```

## 프로젝트 진행 계획

- 10주차: 4인 역할 분담, 1차 완성본 구축 및 공동 작동 검증
- 11주차: 측정 엔진 정밀화와 실제 반복 측정
- 12주차: 규칙 기반 진단 튜닝 및 Upstage Solar 연동
- 13주차: 대시보드·API·E2E 흐름 완성
- 14주차: 유선·Wi-Fi·부하 환경 비교 및 결과 패키지 완성
- 15주차: 통합 점검 및 최종 제출

## 안전 원칙

본인이 권한을 가진 네트워크와 측정을 허용한 서버만 사용합니다. 학교나 타인의
인프라를 대상으로 부하 시험을 하지 않으며, 패킷 감청이나 개인정보 수집 기능은
만들지 않습니다.
