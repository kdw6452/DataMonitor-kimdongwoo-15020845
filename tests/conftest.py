import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_json(tmp_path: Path) -> Path:
    data = {
        "service": "auth",
        "status": "running",
        "metrics": {"requests_per_sec": 100, "error_rate": 0.01},
        "last_updated": "2026-05-08T10:00:00Z",
    }
    p = tmp_path / "state.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


@pytest.fixture
def sample_dir(tmp_path: Path) -> Path:
    files = {
        "service_a.json": {"name": "service_a", "status": "ok"},
        "service_b.json": {"name": "service_b", "status": "degraded"},
    }
    for name, content in files.items():
        (tmp_path / name).write_text(json.dumps(content), encoding="utf-8")
    return tmp_path
