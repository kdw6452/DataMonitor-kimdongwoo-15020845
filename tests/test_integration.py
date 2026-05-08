import json
import time
from pathlib import Path

from datamonitor.config import MonitorConfig
from datamonitor.monitor import ChangeKind, DataMonitor, DiffResult
from datamonitor.renderer import PlainRenderer


class FakeRenderer:
    def __init__(self):
        self.calls: list[list[DiffResult]] = []

    def render(self, results: list[DiffResult], config: MonitorConfig) -> None:
        self.calls.append(results)

    def close(self) -> None:
        pass


class TestEndToEnd:
    def test_initial_load_all_unchanged_or_added(self, sample_json: Path):
        config = MonitorConfig(data_path=str(sample_json), interval=0.2)
        renderer = FakeRenderer()
        monitor = DataMonitor(config)
        monitor.on_update(lambda r: renderer.render(r, config))
        monitor.start()
        time.sleep(0.4)
        monitor.stop()

        first = renderer.calls[0][0]
        assert first.error is None
        kinds = {f.kind for f in first.fields}
        assert ChangeKind.ADDED in kinds or ChangeKind.UNCHANGED in kinds

    def test_detects_change_after_file_update(self, tmp_path: Path):
        path = tmp_path / "live.json"
        path.write_text(json.dumps({"value": 1}), encoding="utf-8")

        config = MonitorConfig(data_path=str(path), interval=0.2)
        renderer = FakeRenderer()
        monitor = DataMonitor(config)
        monitor.on_update(lambda r: renderer.render(r, config))
        monitor.start()
        time.sleep(0.3)

        path.write_text(json.dumps({"value": 99}), encoding="utf-8")
        time.sleep(0.5)
        monitor.stop()

        all_fields = [
            f for batch in renderer.calls for r in batch for f in r.fields
        ]
        changed = [f for f in all_fields if f.kind == ChangeKind.CHANGED]
        assert any(f.key == "value" for f in changed)

    def test_plain_renderer_no_crash(self, sample_json: Path):
        config = MonitorConfig(data_path=str(sample_json), interval=0.2, no_color=True)
        renderer = PlainRenderer()
        monitor = DataMonitor(config)
        monitor.on_update(lambda r: renderer.render(r, config))
        monitor.start()
        time.sleep(0.4)
        monitor.stop()
        renderer.close()

    def test_multiple_files_in_directory(self, sample_dir: Path):
        config = MonitorConfig(data_path=str(sample_dir), interval=0.2)
        renderer = FakeRenderer()
        monitor = DataMonitor(config)
        monitor.on_update(lambda r: renderer.render(r, config))
        monitor.start()
        time.sleep(0.4)
        monitor.stop()

        labels = {r.source_label for batch in renderer.calls for r in batch}
        assert "service_a.json" in labels
        assert "service_b.json" in labels

    def test_file_recovery_after_error(self, tmp_path: Path):
        path = tmp_path / "recover.json"
        path.write_text("{bad json}", encoding="utf-8")

        config = MonitorConfig(data_path=str(path), interval=0.15)
        renderer = FakeRenderer()
        monitor = DataMonitor(config)
        monitor.on_update(lambda r: renderer.render(r, config))
        monitor.start()
        time.sleep(0.25)

        path.write_text(json.dumps({"fixed": True}), encoding="utf-8")
        time.sleep(0.35)
        monitor.stop()

        errors = [r for batch in renderer.calls for r in batch if r.error]
        successes = [r for batch in renderer.calls for r in batch if not r.error]
        assert errors
        assert successes
