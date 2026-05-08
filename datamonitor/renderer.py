from abc import ABC, abstractmethod

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import (
    COLOR_ADDED,
    COLOR_CHANGED,
    COLOR_ERROR,
    COLOR_REMOVED,
    COLOR_UNCHANGED,
    MonitorConfig,
)
from .monitor import ChangeKind, DiffResult

_KIND_COLOR = {
    ChangeKind.ADDED: COLOR_ADDED,
    ChangeKind.REMOVED: COLOR_REMOVED,
    ChangeKind.CHANGED: COLOR_CHANGED,
    ChangeKind.UNCHANGED: COLOR_UNCHANGED,
}

_KIND_LABEL = {
    ChangeKind.ADDED: "[+]",
    ChangeKind.REMOVED: "[-]",
    ChangeKind.CHANGED: "[~]",
    ChangeKind.UNCHANGED: "   ",
}


class Renderer(ABC):
    @abstractmethod
    def render(self, results: list[DiffResult], config: MonitorConfig) -> None: ...

    @abstractmethod
    def close(self) -> None: ...


class RichRenderer(Renderer):
    def __init__(self) -> None:
        self._console = Console()
        self._live = Live(console=self._console, refresh_per_second=4)
        self._live.start()
        self._last_results: list[DiffResult] = []
        self._config: MonitorConfig | None = None

    def render(self, results: list[DiffResult], config: MonitorConfig) -> None:
        self._last_results = results
        self._config = config
        self._live.update(self._build_layout(results, config))

    def close(self) -> None:
        self._live.stop()

    # ── 내부 빌더 ─────────────────────────────────────────

    def _build_layout(
        self, results: list[DiffResult], config: MonitorConfig
    ) -> Panel:
        timestamp = results[0].timestamp if results else "--:--:--"
        header = self._build_header(config, timestamp)
        body = self._build_body(results, config)
        footer = self._build_footer()

        from rich.console import Group

        content = Group(header, body, footer)
        return Panel(content, title="[bold cyan]DataMonitor[/bold cyan]", border_style="cyan")

    def _build_header(self, config: MonitorConfig, timestamp: str) -> Table:
        t = Table.grid(padding=(0, 2))
        t.add_column(style="bold")
        t.add_column()
        t.add_row("Path :", config.data_path)
        t.add_row("Updated :", timestamp)
        t.add_row("Interval :", f"{config.interval}s")
        t.add_row("Filter :", config.filter_pattern or "(none)")
        t.add_row("Mode :", "flat" if config.flat_mode else "tree")
        return t

    def _build_body(self, results: list[DiffResult], config: MonitorConfig) -> Table:
        t = Table(
            show_header=True,
            header_style="bold magenta",
            box=None,
            pad_edge=False,
            expand=True,
        )
        t.add_column("", width=3)
        t.add_column("Source", style="bold", min_width=16)
        t.add_column("Key", min_width=24)
        t.add_column("Value / Change")

        for result in results:
            if result.error:
                t.add_row(
                    "[red]![/red]",
                    Text(result.source_label, style="bold red"),
                    Text("ERROR", style="red"),
                    Text(result.error, style=COLOR_ERROR),
                )
                continue

            for fd in result.fields:
                color = COLOR_UNCHANGED if config.no_color else _KIND_COLOR[fd.kind]
                label = _KIND_LABEL[fd.kind]

                if fd.kind == ChangeKind.ADDED:
                    value_text = Text(str(fd.new_value), style=color)
                elif fd.kind == ChangeKind.REMOVED:
                    value_text = Text(str(fd.old_value), style=color)
                elif fd.kind == ChangeKind.CHANGED:
                    value_text = Text(
                        f"{fd.old_value}  →  {fd.new_value}", style=color
                    )
                else:
                    value_text = Text(str(fd.new_value), style=color)

                t.add_row(
                    Text(label, style=color),
                    Text(result.source_label, style="dim"),
                    Text(fd.key, style=color),
                    value_text,
                )

        if t.row_count == 0:
            t.add_row("", "", Text("(데이터 없음)", style="dim"), "")

        return t

    def _build_footer(self) -> Text:
        return Text(
            "  [q] 종료    [r] 새로고침    [f] 필터 입력",
            style="dim",
        )


class PlainRenderer(Renderer):
    """색상 없는 텍스트 전용 렌더러 (--no-color 또는 비TTY 환경)."""

    def render(self, results: list[DiffResult], config: MonitorConfig) -> None:
        ts = results[0].timestamp if results else ""
        print(f"\n=== DataMonitor [{ts}] ===")
        for result in results:
            if result.error:
                print(f"[ERROR] {result.source_label}: {result.error}")
                continue
            for fd in result.fields:
                label = _KIND_LABEL[fd.kind].strip() or " "
                if fd.kind == ChangeKind.CHANGED:
                    print(
                        f"  {label}  {result.source_label} | "
                        f"{fd.key}: {fd.old_value} -> {fd.new_value}"
                    )
                elif fd.kind != ChangeKind.UNCHANGED:
                    val = fd.new_value if fd.kind == ChangeKind.ADDED else fd.old_value
                    print(f"  {label}  {result.source_label} | {fd.key}: {val}")

    def close(self) -> None:
        pass
