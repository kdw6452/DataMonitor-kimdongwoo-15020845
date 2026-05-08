# plan.md — DataMonitor PoC 구현 로드맵

> 요구사항 전체는 [PRD.md](PRD.md) / 기술 설계는 [Design.md](Design.md) / 프로젝트 규칙은 [CLAUDE.md](../CLAUDE.md) 참조.

---

## 마일스톤 개요

| 단계 | 목표 | 산출물 |
|---|---|---|
| M0 | 프로젝트 뼈대 | 패키지 구조, requirements.txt, 빈 모듈 |
| M1 | 데이터 로드 | DataLoader, 단위 테스트 |
| M2 | 모니터 루프 | Monitor 폴링 루프, diff 엔진 |
| M3 | 콘솔 렌더러 | Renderer (rich), 색상 하이라이트 |
| M4 | CLI & 통합 | `__main__`, argparse, 엔드-투-엔드 테스트 |
| M5 | 필터 & 폴리시 | 필터링, 에러 복원, UX 개선 |
| M6 | 검증 & 문서 | 커버리지 ≥ 70 %, 데모 영상/스크린샷 |

---

## 상세 태스크

### M0 — 프로젝트 뼈대

- [ ] `datamonitor/` 패키지 디렉터리 생성 (`__init__.py`)
- [ ] `requirements.txt` 작성 (`rich>=13`, `pytest`, `flake8`)
- [ ] `data/` 샘플 JSON 파일 2종 생성
- [ ] `tests/` 디렉터리 및 `conftest.py` 생성

### M1 — 데이터 로드 (`data_loader.py`)

- [ ] `load_file(path: Path) -> dict` 구현
- [ ] `load_directory(path: Path) -> dict[str, dict]` 구현
- [ ] 잘못된 JSON 처리 (예외를 잡아 `None` 반환 + 로그)
- [ ] 단위 테스트 작성 (`tests/test_data_loader.py`)

### M2 — 모니터 루프 (`monitor.py`)

- [ ] `DataMonitor` 클래스 설계
  - `start()` / `stop()` 메서드
  - 폴링 스레드 (Thread 또는 asyncio)
- [ ] `diff(old: dict, new: dict) -> DiffResult` 순수 함수 구현
  - 추가·삭제·변경·유지 키 분류
- [ ] 단위 테스트 작성 (`tests/test_monitor.py`)

### M3 — 콘솔 렌더러 (`renderer.py`)

- [ ] `Renderer` 추상 기반 클래스 정의
- [ ] `RichRenderer(Renderer)` 구현
  - `rich.Live` + `rich.Table` 또는 `rich.Tree` 사용
  - 헤더: 경로, 갱신 시각, 인터벌
  - 바디: 변경 색상 하이라이트
  - 푸터: 단축키 안내
- [ ] 색상 매핑 상수 `config.py` 에 정의

### M4 — CLI & 통합 (`__main__.py`)

- [ ] `argparse` 로 CLI 옵션 파싱 (PRD F-06 참조)
- [ ] `Monitor` + `Renderer` 연결 및 실행
- [ ] `q` / `r` / `f` 키 입력 처리
- [ ] 통합 테스트 (`tests/test_integration.py`)

### M5 — 필터 & 폴리시

- [ ] `--filter PATTERN` 키 경로 필터 적용
- [ ] `--flat` 플랫 키-값 출력 모드
- [ ] 파일 삭제·재생성 시나리오 복원 로직
- [ ] `--no-color` 모드

### M6 — 검증 & 마무리

- [ ] `pytest --cov=datamonitor` 커버리지 ≥ 70 % 확인
- [ ] `flake8` 통과
- [ ] README 또는 CLAUDE.md 업데이트
- [ ] 데모 스크린샷 `docs/` 에 추가

---

## 의존 관계 다이어그램

```
M0 ──► M1 ──► M2 ──► M4
                └──► M3 ──► M4
                              └──► M5 ──► M6
```

---

## 리스크

| 리스크 | 대응 |
|---|---|
| Windows 터미널 색상 미지원 | `--no-color` 플래그로 우회, rich의 auto-detect 활용 |
| 대용량 JSON 성능 | PoC 범위는 1 MB 이하로 제한, 초과 시 경고 출력 |
| curses vs rich 선택 | rich로 단일화 (크로스플랫폼 이점) |
