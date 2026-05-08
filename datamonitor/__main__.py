import argparse
import sys
import threading

# 직접 실행(python datamonitor/__main__.py)과 모듈 실행(-m datamonitor) 모두 지원
if __name__ == "__main__" and __package__ is None:
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    __package__ = "datamonitor"

from .config import DEFAULT_INTERVAL, MonitorConfig  # noqa: E402
from .monitor import DataMonitor  # noqa: E402
from .renderer import PlainRenderer, RichRenderer  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m datamonitor",
        description="콘솔 실시간 JSON 데이터 모니터링 도구",
    )
    parser.add_argument(
        "--data-path",
        default="./data",
        metavar="PATH",
        help="JSON 파일 또는 디렉터리 경로 (기본: ./data)",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL,
        metavar="SECONDS",
        help=f"폴링 간격(초) (기본: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--filter",
        dest="filter_pattern",
        default=None,
        metavar="PATTERN",
        help="키 또는 값 필터 패턴",
    )
    parser.add_argument(
        "--flat",
        action="store_true",
        help="중첩 JSON을 플랫 키-값으로 표시 (기본 동작과 동일, 항상 플랫)",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="색상 출력 비활성화",
    )
    return parser.parse_args()


def _read_keys(
    monitor: DataMonitor, renderer, config: MonitorConfig, quit_event: threading.Event
) -> None:
    """메인 스레드에서 키 입력을 처리한다."""
    import msvcrt  # Windows

    def _get_char() -> str:
        try:
            if msvcrt.kbhit():
                ch = msvcrt.getwch()
                return ch
        except Exception:
            pass
        return ""

    import time
    while not quit_event.is_set():
        ch = _get_char()
        if ch:
            if ch.lower() == "q":
                quit_event.set()
            elif ch.lower() == "r":
                monitor.force_refresh()
            elif ch.lower() == "f":
                # Live 일시 중단 후 필터 입력
                renderer.close()
                new_pattern = input("필터 패턴 입력 (빈값=초기화): ").strip() or None
                config.filter_pattern = new_pattern
                renderer.__init__()
                monitor.on_update(lambda r: renderer.render(r, config))
        time.sleep(0.05)


def _read_keys_unix(
    monitor: DataMonitor, renderer, config: MonitorConfig, quit_event: threading.Event
) -> None:
    """Unix 계열 키 입력 처리."""
    import sys
    import termios
    import tty
    import select

    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while not quit_event.is_set():
            r, _, _ = select.select([sys.stdin], [], [], 0.05)
            if r:
                ch = sys.stdin.read(1)
                if ch.lower() == "q":
                    quit_event.set()
                elif ch.lower() == "r":
                    monitor.force_refresh()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def main() -> None:
    args = parse_args()
    config = MonitorConfig(
        data_path=args.data_path,
        interval=args.interval,
        filter_pattern=args.filter_pattern,
        flat_mode=args.flat,
        no_color=args.no_color,
    )

    renderer = PlainRenderer() if args.no_color else RichRenderer()
    monitor = DataMonitor(config)
    monitor.on_update(lambda results: renderer.render(results, config))

    quit_event = threading.Event()

    try:
        monitor.start()

        if sys.platform == "win32":
            _read_keys(monitor, renderer, config, quit_event)
        else:
            _read_keys_unix(monitor, renderer, config, quit_event)

    except KeyboardInterrupt:
        pass
    finally:
        monitor.stop()
        renderer.close()
        print("\n[DataMonitor] 종료.")


if __name__ == "__main__":
    main()
