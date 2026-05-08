# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DataMonitor PoC — Python 기반의 콘솔 실시간 데이터 모니터링 관리자 도구.
JSON 형태의 데이터를 실시간으로 조회·감시하는 CLI 도구.

상세 요구사항 및 설계는 아래 문서를 참조:

- **PRD** (제품 요구사항): [`docs/PRD.md`](docs/PRD.md)
- **계획** (구현 로드맵): [`docs/plan.md`](docs/plan.md)
- **설계** (기술 아키텍처): [`docs/Design.md`](docs/Design.md)

## Commands

```bash
# 의존성 설치
pip install -r requirements.txt

# 모니터 실행 (기본)
python -m datamonitor

# 모니터 실행 (옵션 지정)
python -m datamonitor --data-path ./data --interval 2

# 테스트 실행
pytest

# 단일 테스트 실행
pytest tests/test_monitor.py::test_name -v

# 린트
flake8 datamonitor/ tests/
```

## Architecture

```
DataMonitor_PoC/
├── datamonitor/          # 패키지 루트
│   ├── __main__.py       # 진입점 (CLI 파싱)
│   ├── monitor.py        # 핵심 모니터링 루프
│   ├── data_loader.py    # JSON 파일 읽기·파싱
│   ├── renderer.py       # 콘솔 UI 렌더링 (curses / rich)
│   └── config.py         # 설정값 및 상수
├── data/                 # 샘플 JSON 데이터 파일
├── tests/                # pytest 테스트
├── docs/                 # 설계 문서
└── requirements.txt
```

### 핵심 데이터 흐름

```
JSON 파일 / stdin
      │
  DataLoader          ← 주기적 폴링 or inotify 감시
      │
  Monitor (루프)      ← 상태 diff·집계
      │
  Renderer            ← 터미널 출력 (실시간 갱신)
```

- `Monitor`가 주 루프를 소유하며 `DataLoader`와 `Renderer`를 조율한다.
- `DataLoader`는 순수 함수 형태로 유지해 테스트를 쉽게 한다.
- `Renderer`는 출력 백엔드(rich / curses / plain)를 추상화한다.

## Key Conventions

- Python 3.11+, 타입 힌트 필수
- 외부 의존성은 `requirements.txt`에 고정 버전으로 기록
- JSON 스키마 변경은 `docs/Design.md`의 데이터 모델 섹션도 함께 갱신
