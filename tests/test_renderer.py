from unittest.mock import MagicMock, patch

from datamonitor.config import MonitorConfig
from datamonitor.monitor import ChangeKind, DiffResult, FieldDiff
from datamonitor.renderer import PlainRenderer, RichRenderer, _KIND_COLOR, _KIND_LABEL


def _config(**kwargs) -> MonitorConfig:
    defaults = dict(data_path="./data", interval=2.0)
    defaults.update(kwargs)
    return MonitorConfig(**defaults)


def _make_result(kind: ChangeKind, key: str = "x", label: str = "f.json") -> DiffResult:
    fd = FieldDiff(
        key=key,
        kind=kind,
        old_value="old" if kind in (ChangeKind.REMOVED, ChangeKind.CHANGED) else None,
        new_value="new" if kind in (ChangeKind.ADDED, ChangeKind.CHANGED) else None,
    )
    if kind == ChangeKind.UNCHANGED:
        fd.old_value = "v"
        fd.new_value = "v"
    return DiffResult(fields=[fd], timestamp="12:00:00", source_label=label)


def _error_result(label: str = "bad.json") -> DiffResult:
    return DiffResult(error="JSON 파싱 오류", timestamp="12:00:00", source_label=label)


class TestKindMappings:
    def test_all_kinds_have_color(self):
        for kind in ChangeKind:
            assert kind in _KIND_COLOR

    def test_all_kinds_have_label(self):
        for kind in ChangeKind:
            assert kind in _KIND_LABEL


class TestPlainRenderer:
    def test_render_does_not_crash(self, capsys):
        renderer = PlainRenderer()
        config = _config()
        renderer.render([_make_result(ChangeKind.ADDED)], config)
        out = capsys.readouterr().out
        assert "DataMonitor" in out

    def test_render_changed(self, capsys):
        renderer = PlainRenderer()
        renderer.render([_make_result(ChangeKind.CHANGED)], _config())
        out = capsys.readouterr().out
        assert "old" in out
        assert "new" in out

    def test_render_removed(self, capsys):
        renderer = PlainRenderer()
        renderer.render([_make_result(ChangeKind.REMOVED)], _config())
        out = capsys.readouterr().out
        assert "[-]" in out

    def test_render_unchanged_not_printed(self, capsys):
        renderer = PlainRenderer()
        renderer.render([_make_result(ChangeKind.UNCHANGED)], _config())
        out = capsys.readouterr().out
        assert "[-]" not in out
        assert "[+]" not in out
        assert "[~]" not in out

    def test_render_error(self, capsys):
        renderer = PlainRenderer()
        renderer.render([_error_result()], _config())
        out = capsys.readouterr().out
        assert "ERROR" in out

    def test_close_no_crash(self):
        PlainRenderer().close()

    def test_multiple_results(self, capsys):
        renderer = PlainRenderer()
        results = [
            _make_result(ChangeKind.ADDED, label="a.json"),
            _make_result(ChangeKind.REMOVED, label="b.json"),
        ]
        renderer.render(results, _config())
        out = capsys.readouterr().out
        assert "[+]" in out
        assert "[-]" in out

    def test_empty_results(self, capsys):
        renderer = PlainRenderer()
        renderer.render([], _config())
        capsys.readouterr()


class TestRichRenderer:
    def _make_renderer(self):
        with patch("datamonitor.renderer.Live") as mock_live_cls:
            mock_live = MagicMock()
            mock_live_cls.return_value = mock_live
            renderer = RichRenderer()
            renderer._live = mock_live
            return renderer

    def test_render_calls_live_update(self):
        renderer = self._make_renderer()
        config = _config()
        results = [_make_result(ChangeKind.ADDED)]
        renderer.render(results, config)
        renderer._live.update.assert_called_once()

    def test_render_error_result(self):
        renderer = self._make_renderer()
        renderer.render([_error_result()], _config())
        renderer._live.update.assert_called_once()

    def test_render_all_change_kinds(self):
        renderer = self._make_renderer()
        for kind in ChangeKind:
            renderer.render([_make_result(kind)], _config())

    def test_render_no_color_mode(self):
        renderer = self._make_renderer()
        renderer.render([_make_result(ChangeKind.CHANGED)], _config(no_color=True))
        renderer._live.update.assert_called()

    def test_close_stops_live(self):
        renderer = self._make_renderer()
        renderer.close()
        renderer._live.stop.assert_called_once()

    def test_render_with_filter(self):
        renderer = self._make_renderer()
        renderer.render([_make_result(ChangeKind.ADDED)], _config(filter_pattern="x"))
        renderer._live.update.assert_called_once()

    def test_render_empty_fields(self):
        renderer = self._make_renderer()
        empty = DiffResult(fields=[], timestamp="12:00:00", source_label="f.json")
        renderer.render([empty], _config())
        renderer._live.update.assert_called_once()


class TestParseArgs:
    def test_defaults(self):
        from datamonitor.__main__ import parse_args
        with patch("sys.argv", ["datamonitor"]):
            args = parse_args()
        assert args.data_path == "./data"
        assert args.interval == 2.0
        assert args.filter_pattern is None
        assert args.flat is False
        assert args.no_color is False

    def test_custom_path(self):
        from datamonitor.__main__ import parse_args
        with patch("sys.argv", ["datamonitor", "--data-path", "/tmp/data"]):
            args = parse_args()
        assert args.data_path == "/tmp/data"

    def test_interval(self):
        from datamonitor.__main__ import parse_args
        with patch("sys.argv", ["datamonitor", "--interval", "5"]):
            args = parse_args()
        assert args.interval == 5.0

    def test_filter_pattern(self):
        from datamonitor.__main__ import parse_args
        with patch("sys.argv", ["datamonitor", "--filter", "status"]):
            args = parse_args()
        assert args.filter_pattern == "status"

    def test_flat_flag(self):
        from datamonitor.__main__ import parse_args
        with patch("sys.argv", ["datamonitor", "--flat"]):
            args = parse_args()
        assert args.flat is True

    def test_no_color_flag(self):
        from datamonitor.__main__ import parse_args
        with patch("sys.argv", ["datamonitor", "--no-color"]):
            args = parse_args()
        assert args.no_color is True
