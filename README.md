# NetDoctor

NetDoctor는 DNS 조회, TCP 연결, HTTP 응답 시작 시간(TTFB), 다운로드 처리율,
RTT를 측정해 사용자가 이해할 수 있는 말로 네트워크 상태를 설명하는 프로젝트입니다.

현재 저장소에는 **1주차 설계 및 실행 골격**이 구현되어 있습니다. 실제 네트워크
측정은 2주차 범위이며, 지금은 측정 계획·데이터 계약·설정 검증·대시보드
와이어프레임을 확인할 수 있습니다.

## 빠른 시작

Python 3.11 이상이 필요합니다. 별도 패키지 설치 없이 저장소 루트에서 실행할 수
있습니다.

```powershell
python -m netdoctor plan
python -m netdoctor demo
python -m netdoctor demo --json
python -m netdoctor dashboard --port 8000
```

마지막 명령을 실행한 뒤 <http://127.0.0.1:8000>을 열면 대시보드 초안을 볼 수
있습니다. 종료할 때는 `Ctrl+C`를 누릅니다.

설치형 명령을 사용하고 싶다면 다음과 같이 개발 모드로 설치합니다.

```powershell
python -m pip install -e .
netdoctor plan
```

## 설정

기본 설정과 같은 형식의 편집용 예시는 [`config/default.json`](config/default.json)에
있습니다. `--config`를 생략하면 프로그램에 내장된 동일한 기본값을 사용합니다.

```powershell
python -m netdoctor --config config/default.json plan
```

반복 횟수는 프로젝트 요구사항에 맞춰 5~10회만 허용합니다. 다운로드 URL은 2주차에
본인 또는 측정을 허용한 서버로 지정할 예정이므로 현재 기본값은 `null`입니다.

## 테스트

```powershell
python -m unittest discover -s tests -v
```

## 문서

- [`docs/week1-design.md`](docs/week1-design.md): 측정 정의, 구조, 데이터 계약, 윤리
- [`docs/roadmap.md`](docs/roadmap.md): 5주 개발 로드맵과 주차별 완료 조건

## 현재 범위

- [x] 프로젝트 구조와 Python 패키지 구성
- [x] 측정 대상·반복 횟수·타임아웃 설정 및 검증
- [x] 통계와 측정 결과 데이터 모델
- [x] CLI 계획 출력과 명시적인 데모 결과
- [x] 반응형 웹 대시보드 와이어프레임
- [x] 단위 테스트
- [ ] 실제 DNS/TCP/TTFB/다운로드/RTT 측정
- [ ] 규칙 기반 진단
- [ ] 실제 측정 API와 대시보드 연결

## 안전 원칙

본인이 권한을 가진 네트워크와 서버만 측정합니다. 학교나 타인의 인프라를 대상으로
부하 시험을 하지 않으며, 패킷 감청이나 개인정보 수집 기능은 만들지 않습니다.
