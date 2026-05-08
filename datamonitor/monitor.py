import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path

from .config import MonitorConfig
from .data_loader import apply_filter, flatten, load_directory, load_file


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
    source_label: str = ""
    error: str | None = None

    @property
    def has_changes(self) -> bool:
        return any(f.kind != ChangeKind.UNCHANGED for f in self.fields)


def diff(old: dict[str, object], new: dict[str, object]) -> list[FieldDiff]:
    """두 플랫 dict를 비교해 FieldDiff 목록 반환."""
    all_keys = sorted(old.keys() | new.keys())
    result: list[FieldDiff] = []
    for key in all_keys:
        if key not in old:
            result.append(FieldDiff(key, ChangeKind.ADDED, new_value=new[key]))
        elif key not in new:
            result.append(FieldDiff(key, ChangeKind.REMOVED, old_value=old[key]))
        elif old[key] != new[key]:
            result.append(FieldDiff(key, ChangeKind.CHANGED, old[key], new[key]))
        else:
            result.append(FieldDiff(key, ChangeKind.UNCHANGED, old[key], new[key]))
    return result


class DataMonitor:
    def __init__(self, config: MonitorConfig) -> None:
        self._config = config
        self._callbacks: list[Callable[[list[DiffResult]], None]] = []
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._snapshots: dict[str, dict[str, object]] = {}

    def on_update(self, callback: Callable[[list[DiffResult]], None]) -> None:
        self._callbacks.append(callback)

    def start(self) -> None:
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def force_refresh(self) -> None:
        self._stop_event.set()
        self._stop_event.clear()
        t = threading.Thread(target=self._poll_once, daemon=True)
        t.start()

    def _loop(self) -> None:
        self._poll_once()
        while not self._stop_event.wait(timeout=self._config.interval):
            self._poll_once()

    def _poll_once(self) -> None:
        path = Path(self._config.data_path)
        results: list[DiffResult] = []

        if path.is_dir():
            entries = load_directory(path)
            for filename, (data, error) in entries.items():
                results.append(self._make_diff(filename, data, error))
        else:
            data, error = load_file(path)
            results.append(self._make_diff(path.name, data, error))

        if results:
            ts = datetime.now().strftime("%H:%M:%S")
            for r in results:
                r.timestamp = ts
            self._notify(results)

    def _make_diff(
        self,
        label: str,
        data: dict | None,
        error: str | None,
    ) -> DiffResult:
        if data is None:
            return DiffResult(source_label=label, error=error)

        new_flat = flatten(data)
        if self._config.filter_pattern:
            new_flat = apply_filter(new_flat, self._config.filter_pattern)

        old_flat = self._snapshots.get(label, {})
        fields = diff(old_flat, new_flat)
        self._snapshots[label] = new_flat

        return DiffResult(fields=fields, source_label=label)

    def _notify(self, results: list[DiffResult]) -> None:
        for cb in self._callbacks:
            cb(results)
