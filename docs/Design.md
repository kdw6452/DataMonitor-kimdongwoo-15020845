# Design.md — DataMonitor PoC 기술 설계

> 요구사항은 [PRD.md](PRD.md) / 구현 순서는 [plan.md](plan.md) / 프로젝트 규칙은 [CLAUDE.md](../CLAUDE.md) 참조.

---

## 1. 시스템 구성도

```
┌─────────────────────────────────────────────┐
│                  Terminal                   │
│  ┌───────────────────────────────────────┐  │
│  │            Renderer (rich)            │  │
│  │  Header │ JSON Tree / Flat KV │ Footer│  │
│  └───────────────────────────────────────┘  │
│                     ▲                       │
│              RenderEvent(DiffResult)        │
│                     │                       │
│  ┌──────────────────┴──────────────────┐   │
│  │           DataMonitor               │   │
│  │  polling thread  │  diff engine     │   │
│  └──────────────────┬──────────────────┘   │
│                     │                       │
│  ┌──────────────────▼──────────────────┐   │
│  │           DataLoader                │   │
│  │   load_file() / load_directory()    │   │
│  └──────────────────┬──────────────────┘   │
│                     │                       │
│           JSON File(s) on disk             │
└─────────────────────────────────────────────┘
```

---

## 2. 모듈 설계

### 2-1. `config.py`

설정 상수와 색상 매핑만 담는다. 비즈니스 로직 없음.

```python
from dataclasses import dataclass

DEFAULT_INTERVAL: float = 2.0
MAX_FILE_SIZE_MB: int = 1

COLOR_ADDED    = "green"
COLOR_REMOVED  = "red"
COLOR_CHANGED  = "yellow"
COLOR_UNCHANGED = "default"

@dataclass
class MonitorConfig:
    data_path: str
    interval: float = DEFAULT_INTERVAL
    filter_pattern: str | None = None
    flat_mode: bool = False
    no_color: bool = False
```

---

### 2-2. `data_loader.py`

순수 함수 모듈 — 사이드 이펙트는 파일 읽기뿐.

```python
from pathlib import Path

def load_file(path: Path) -> dict | None:
    """JSON 파일을 읽어 dict 반환. 실패 시 None."""

def load_directory(path: Path) -> dict[str, dict | None]:
    """디렉터리 내 *.json 파일을 {filename: dict} 로 반환."""

def flatten(data: dict, sep: str = ".") -> dict[str, object]:
    """중첩 dict를 dot-notation 플랫 dict로 변환."""
```

**에러 처리 규칙:**
- `json.JSONDecodeError` → `None` 반환 + 오류 메시지 반환값에 포함
- 파일 없음 / 권한 오류 → `None` 반환

---

### 2-3. `monitor.py`

상태 관리 및 폴링 루프.

```python
from dataclasses import dataclass, field
from enum import Enum

class ChangeKind(Enum):
    ADDED = "added"
    REMOVED = "removed"
    CHANGED = "changed"
    UNCHANGED = "unchanged"

@dataclass
class FieldDiff:
    key: str
    kind: ChangeKind
    old_value: object = None
    new_value: object = None

@dataclass
class DiffResult:
    fields: list[FieldDiff] = field(default_factory=list)
    timestamp: str = ""

class DataMonitor:
    def __init__(self, config: MonitorConfig): ...
    def start(self) -> None: ...   # 폴링 스레드 시작
    def stop(self) -> None: ...    # 스레드 정지 + 리소스 해제
    def on_update(self, callback: Callable[[DiffResult], None]): ...
```

**폴링 전략:**
- `threading.Thread` + `threading.Event` (stop signal)
- 간격마다 `DataLoader` 호출 → 이전 스냅샷과 `diff()` 비교 → 콜백 호출

**diff 알고리즘:**
```
1. 두 플랫 dict의 키 합집합을 순회
2. 신규 키 → ADDED
3. 사라진 키 → REMOVED
4. 값이 달라진 키 → CHANGED
5. 동일한 키 → UNCHANGED
```

---

### 2-4. `renderer.py`

출력 백엔드 추상화.

```python
from abc import ABC, abstractmethod

class Renderer(ABC):
    @abstractmethod
    def render(self, diff: DiffResult, config: MonitorConfig) -> None: ...
    @abstractmethod
    def close(self) -> None: ...

class RichRenderer(Renderer):
    """rich.Live 기반 렌더러."""
    def render(self, diff: DiffResult, config: MonitorConfig) -> None: ...
    def close(self) -> None: ...
```

**레이아웃 (rich.Layout):**

```
┌─ Header ──────────────────────────────────────┐
│ Path: ./data/state.json  Updated: 12:34:56    │
│ Interval: 2s             Filter: (none)        │
├─ Body ────────────────────────────────────────┤
│  key.path        old_value  →  new_value       │
│  ...                                           │
├─ Footer ──────────────────────────────────────┤
│  [q] Quit  [r] Refresh  [f] Filter            │
└───────────────────────────────────────────────┘
```

---

### 2-5. `__main__.py`

진입점 — argparse + 조립.

```python
def main():
    args = parse_args()
    config = MonitorConfig(...)
    renderer = RichRenderer()
    monitor = DataMonitor(config)
    monitor.on_update(renderer.render)
    monitor.start()
    wait_for_quit_key()   # 'q' 입력 대기
    monitor.stop()
    renderer.close()
```

---

## 3. 데이터 모델

### 입력 JSON 예시

```json
{
  "service": "auth",
  "status": "running",
  "metrics": {
    "requests_per_sec": 142,
    "error_rate": 0.02
  },
  "last_updated": "2026-05-08T10:00:00Z"
}
```

### JSON 스키마 규칙 (PoC 범위)

- 최상위 타입은 `object` 또는 `array of objects`.
- 중첩 깊이 제한 없음, 단 플랫 모드에서는 dot-notation으로 전개.
- 스키마 변경 시 이 섹션을 함께 갱신할 것.

---

## 4. 키 입력 처리

`rich`의 `Live` 컨텍스트 외부에서 `readchar` 또는 `threading` + `sys.stdin` 으로 키 이벤트를 수신한다.

| 키 | 동작 |
|---|---|
| `q` / `Q` | 모니터 종료 |
| `r` / `R` | 수동 새로고침 (폴링 주기 무시) |
| `f` / `F` | 인라인 필터 패턴 입력 모드 |

---

## 5. 의존성

| 라이브러리 | 용도 | 버전 |
|---|---|---|
| `rich` | 터미널 UI (색상, 레이아웃, Live 갱신) | ≥ 13.0 |
| `pytest` | 단위·통합 테스트 | ≥ 8.0 |
| `pytest-cov` | 커버리지 측정 | ≥ 5.0 |
| `flake8` | 린트 | ≥ 7.0 |

표준 라이브러리만 사용: `json`, `pathlib`, `threading`, `argparse`, `time`, `datetime`.

---

## 6. 테스트 전략

| 레이어 | 도구 | 대상 |
|---|---|---|
| 단위 | pytest | `data_loader`, `monitor.diff` — 순수 함수 위주 |
| 통합 | pytest + tmp_path | 파일 변경 → diff 이벤트 흐름 전체 |
| 렌더러 | 수동 / 스크린샷 | RichRenderer 시각 검증 |

렌더러는 추상 기반(`Renderer`)을 사용하므로 테스트에서 `FakeRenderer`로 치환 가능.
