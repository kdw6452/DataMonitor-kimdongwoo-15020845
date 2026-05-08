import json
from pathlib import Path

from .config import MAX_FILE_SIZE_MB


def load_file(path: Path) -> tuple[dict | None, str | None]:
    """JSON 파일을 읽어 (data, error_msg) 반환. 실패 시 data=None."""
    try:
        size_mb = path.stat().st_size / (1024 * 1024)
        if size_mb > MAX_FILE_SIZE_MB:
            return None, f"파일 크기 초과: {size_mb:.1f} MB (한도 {MAX_FILE_SIZE_MB} MB)"
        text = path.read_text(encoding="utf-8")
        return json.loads(text), None
    except FileNotFoundError:
        return None, f"파일 없음: {path}"
    except PermissionError:
        return None, f"접근 권한 없음: {path}"
    except json.JSONDecodeError as e:
        return None, f"JSON 파싱 오류: {e}"
    except OSError as e:
        return None, f"파일 읽기 오류: {e}"


def load_directory(path: Path) -> dict[str, tuple[dict | None, str | None]]:
    """디렉터리 내 *.json 파일을 {filename: (data, error)} 로 반환."""
    if not path.is_dir():
        return {}
    return {
        f.name: load_file(f)
        for f in sorted(path.glob("*.json"))
    }


def flatten(data: object, sep: str = ".", _prefix: str = "") -> dict[str, object]:
    """중첩 dict/list를 dot-notation 플랫 dict로 변환."""
    items: dict[str, object] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{_prefix}{sep}{k}" if _prefix else k
            items.update(flatten(v, sep=sep, _prefix=new_key))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            new_key = f"{_prefix}{sep}{i}" if _prefix else str(i)
            items.update(flatten(v, sep=sep, _prefix=new_key))
    else:
        items[_prefix] = data
    return items


def apply_filter(flat: dict[str, object], pattern: str) -> dict[str, object]:
    """키 또는 값에 pattern이 포함된 항목만 반환 (대소문자 무시)."""
    p = pattern.lower()
    return {
        k: v for k, v in flat.items()
        if p in k.lower() or p in str(v).lower()
    }
