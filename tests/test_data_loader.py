from pathlib import Path

from datamonitor.data_loader import apply_filter, flatten, load_directory, load_file


class TestLoadFile:
    def test_valid_json(self, sample_json: Path):
        data, err = load_file(sample_json)
        assert err is None
        assert data["service"] == "auth"

    def test_file_not_found(self, tmp_path: Path):
        data, err = load_file(tmp_path / "missing.json")
        assert data is None
        assert "파일 없음" in err

    def test_invalid_json(self, tmp_path: Path):
        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json}", encoding="utf-8")
        data, err = load_file(bad)
        assert data is None
        assert "JSON 파싱 오류" in err

    def test_file_too_large(self, tmp_path: Path, monkeypatch):
        big = tmp_path / "big.json"
        big.write_text("{}", encoding="utf-8")
        monkeypatch.setattr(
            "datamonitor.data_loader.MAX_FILE_SIZE_MB", 0
        )
        data, err = load_file(big)
        assert data is None
        assert "초과" in err


class TestLoadDirectory:
    def test_loads_json_files(self, sample_dir: Path):
        result = load_directory(sample_dir)
        assert "service_a.json" in result
        assert "service_b.json" in result

    def test_returns_empty_for_non_dir(self, tmp_path: Path):
        f = tmp_path / "file.json"
        f.write_text("{}", encoding="utf-8")
        assert load_directory(f) == {}

    def test_data_content(self, sample_dir: Path):
        result = load_directory(sample_dir)
        data, err = result["service_a.json"]
        assert err is None
        assert data["name"] == "service_a"


class TestFlatten:
    def test_flat_dict(self):
        assert flatten({"a": 1, "b": 2}) == {"a": 1, "b": 2}

    def test_nested_dict(self):
        result = flatten({"a": {"b": {"c": 42}}})
        assert result == {"a.b.c": 42}

    def test_list_values(self):
        result = flatten({"items": [10, 20]})
        assert result == {"items.0": 10, "items.1": 20}

    def test_empty(self):
        assert flatten({}) == {}

    def test_scalar(self):
        assert flatten("hello") == {"": "hello"}

    def test_custom_sep(self):
        result = flatten({"a": {"b": 1}}, sep="/")
        assert result == {"a/b": 1}


class TestApplyFilter:
    def test_key_match(self):
        data = {"status": "ok", "error_rate": 0.02, "name": "auth"}
        result = apply_filter(data, "error")
        assert "error_rate" in result
        assert "status" not in result

    def test_value_match(self):
        data = {"status": "running", "mode": "standby"}
        result = apply_filter(data, "run")
        assert "status" in result
        assert "mode" not in result

    def test_case_insensitive(self):
        data = {"STATUS": "OK"}
        assert apply_filter(data, "status") == {"STATUS": "OK"}

    def test_no_match(self):
        assert apply_filter({"a": 1}, "zzz") == {}
