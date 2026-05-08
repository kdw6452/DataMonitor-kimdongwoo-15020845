from dataclasses import dataclass, field

DEFAULT_INTERVAL: float = 2.0
MAX_FILE_SIZE_MB: int = 1

COLOR_ADDED: str = "green"
COLOR_REMOVED: str = "red"
COLOR_CHANGED: str = "yellow"
COLOR_UNCHANGED: str = "white"
COLOR_ERROR: str = "red"


@dataclass
class MonitorConfig:
    data_path: str
    interval: float = DEFAULT_INTERVAL
    filter_pattern: str | None = None
    flat_mode: bool = False
    no_color: bool = False
    extra_paths: list[str] = field(default_factory=list)
