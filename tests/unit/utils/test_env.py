"""Tests for kicad_mcp.utils.env."""

import os

import pytest

from kicad_mcp.utils.env import find_env_file, get_env_list, load_dotenv


class TestLoadDotenv:
    """Tests for load_dotenv function."""

    def test_load_basic_env_file(self, tmp_path: pytest.TempPathFactory) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("FOO=bar\nBAZ=qux\n")
        result = load_dotenv(str(env_file))
        assert result["FOO"] == "bar"
        assert result["BAZ"] == "qux"
        # Clean up
        os.environ.pop("FOO", None)
        os.environ.pop("BAZ", None)

    def test_load_skips_comments_and_blank_lines(self, tmp_path: pytest.TempPathFactory) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("# comment\n\nKEY1=value1\n")
        result = load_dotenv(str(env_file))
        assert result == {"KEY1": "value1"}
        os.environ.pop("KEY1", None)

    def test_load_strips_quotes(self, tmp_path: pytest.TempPathFactory) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("DOUBLE=\"hello\"\nSINGLE='world'\n")
        result = load_dotenv(str(env_file))
        assert result["DOUBLE"] == "hello"
        assert result["SINGLE"] == "world"
        os.environ.pop("DOUBLE", None)
        os.environ.pop("SINGLE", None)

    def test_load_expands_tilde(self, tmp_path: pytest.TempPathFactory) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("MY_PATH=~/some/path\n")
        result = load_dotenv(str(env_file))
        assert "~" not in result["MY_PATH"]
        assert result["MY_PATH"].endswith("/some/path")
        os.environ.pop("MY_PATH", None)

    def test_load_nonexistent_file_returns_empty(self) -> None:
        result = load_dotenv("/nonexistent/path/.env")
        assert result == {}

    def test_load_sets_environ(self, tmp_path: pytest.TempPathFactory) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("TEST_ENV_VAR_XYZ=123\n")
        load_dotenv(str(env_file))
        assert os.environ.get("TEST_ENV_VAR_XYZ") == "123"
        os.environ.pop("TEST_ENV_VAR_XYZ", None)

    def test_load_skips_lines_without_equals(self, tmp_path: pytest.TempPathFactory) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("no_equals_here\nVALID=yes\n")
        result = load_dotenv(str(env_file))
        assert "no_equals_here" not in result
        assert result["VALID"] == "yes"
        os.environ.pop("VALID", None)


class TestFindEnvFile:
    """Tests for find_env_file function."""

    def test_find_in_current_dir(self, tmp_path: pytest.TempPathFactory, monkeypatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("X=1\n")
        monkeypatch.chdir(tmp_path)
        result = find_env_file()
        assert result is not None
        assert result.endswith(".env")

    def test_find_returns_none_when_missing(
        self, tmp_path: pytest.TempPathFactory, monkeypatch
    ) -> None:
        monkeypatch.chdir(tmp_path)
        result = find_env_file()
        assert result is None

    def test_find_in_parent_dir(self, tmp_path: pytest.TempPathFactory, monkeypatch) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("X=1\n")
        child = tmp_path / "subdir"
        child.mkdir()
        monkeypatch.chdir(child)
        result = find_env_file()
        assert result is not None


class TestGetEnvList:
    """Tests for get_env_list function."""

    def test_comma_separated(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_LIST", "a, b, c")
        result = get_env_list("TEST_LIST")
        assert result == ["a", "b", "c"]

    def test_empty_default(self) -> None:
        result = get_env_list("NONEXISTENT_VAR_XYZ123")
        assert result == []

    def test_custom_default(self, monkeypatch) -> None:
        # Ensure the var is not set
        monkeypatch.delenv("MISSING_VAR", raising=False)
        result = get_env_list("MISSING_VAR", default="x,y")
        assert result == ["x", "y"]

    def test_filters_empty_items(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_LIST2", "a,,b,")
        result = get_env_list("TEST_LIST2")
        assert result == ["a", "b"]
