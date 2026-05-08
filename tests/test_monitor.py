import time
from pathlib import Path

from datamonitor.config import MonitorConfig
from datamonitor.monitor import ChangeKind, DataMonitor, DiffResult, diff


class TestDiff:
    def test_all_unchanged(self):
        old = {"a": 1, "b": 2}
        result = diff(old, old.copy())
        assert all(f.kind == ChangeKind.UNCHANGED for f in result)

    def test_added_key(self):
        fields = diff({}, {"x": 99})
        assert len(fields) == 1
        assert fields[0].kind == ChangeKind.ADDED
        assert fields[0].key == "x"
        assert fields[0].new_value == 99

    def test_removed_key(self):
        fields = diff({"x": 99}, {})
        assert fields[0].kind == ChangeKind.REMOVED
        assert fields[0].old_value == 99

    def test_changed_key(self):
        fields = diff({"x": 1}, {"x": 2})
        assert fields[0].kind == ChangeKind.CHANGED
        assert fields[0].old_value == 1
        assert fields[0].new_value == 2

    def test_mixed(self):
        old = {"keep": "v", "del": "x"}
        new = {"keep": "v", "add": "y"}
        kinds = {f.key: f.kind for f in diff(old, new)}
        assert kinds["keep"] == ChangeKind.UNCHANGED
        assert kinds["del"] == ChangeKind.REMOVED
        assert kinds["add"] == ChangeKind.ADDED

    def test_sorted_keys(self):
        keys = [f.key for f in diff({"b": 1, "a": 2}, {"a": 2, "b": 1})]
        assert keys == sorted(keys)


class TestDiffResult:
    def test_has_changes_true(self):
        from datamonitor.monitor import FieldDiff
        r = DiffResult(fields=[FieldDiff("k", ChangeKind.ADDED, new_value=1)])
        assert r.has_changes is True

    def test_has_changes_false(self):
        from datamonitor.monitor import FieldDiff
        r = DiffResult(fields=[FieldDiff("k", ChangeKind.UNCHANGED, new_value=1)])
        assert r.has_changes is False


class TestDataMonitor:
    def test_start_stop(self, sample_json: Path):
        config = MonitorConfig(data_path=str(sample_json))
        monitor = DataMonitor(config)
        monitor.start()
        time.sleep(0.1)
        monitor.stop()

    def test_callback_called(self, sample_json: Path):
        config = MonitorConfig(data_path=str(sample_json), interval=0.2)
        monitor = DataMonitor(config)
        received: list[list[DiffResult]] = []
        monitor.on_update(received.append)
        monitor.start()
        time.sleep(0.5)
        monitor.stop()
        assert len(received) >= 1

    def test_callback_with_directory(self, sample_dir: Path):
        config = MonitorConfig(data_path=str(sample_dir), interval=0.2)
        monitor = DataMonitor(config)
        received: list[list[DiffResult]] = []
        monitor.on_update(received.append)
        monitor.start()
        time.sleep(0.5)
        monitor.stop()
        assert len(received) >= 1
        first_batch = received[0]
        labels = {r.source_label for r in first_batch}
        assert "service_a.json" in labels

    def test_filter_applied(self, sample_json: Path):
        config = MonitorConfig(
            data_path=str(sample_json), interval=0.2, filter_pattern="status"
        )
        monitor = DataMonitor(config)
        received: list[list[DiffResult]] = []
        monitor.on_update(received.append)
        monitor.start()
        time.sleep(0.5)
        monitor.stop()
        keys = [f.key for r in received[0] for f in r.fields]
        assert all("status" in k.lower() for k in keys)

    def test_error_result_on_bad_file(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{bad}", encoding="utf-8")
        config = MonitorConfig(data_path=str(bad), interval=0.2)
        monitor = DataMonitor(config)
        received: list[list[DiffResult]] = []
        monitor.on_update(received.append)
        monitor.start()
        time.sleep(0.5)
        monitor.stop()
        assert received[0][0].error is not None
