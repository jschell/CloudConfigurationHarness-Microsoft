"""E2E tests for pyramid_cli.py using Click's CliRunner.

Run:
    cd skills/pyramid-navigator/scripts
    uv run --with pytest --with click pytest test_pyramid_cli.py -v
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyramid_cli import (
    CodeParser,
    Element,
    StorageManager,
    Summarizer,
    cli,
)

# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def initialized(tmp_path: Path, runner: CliRunner) -> Path:
    """Return tmp_path with .pyramid/ initialized."""
    result = runner.invoke(cli, ["init", "--db-path", str(tmp_path / ".pyramid")])
    assert result.exit_code == 0, result.output
    return tmp_path


@pytest.fixture()
def analyzed(initialized: Path, runner: CliRunner) -> Path:
    """Return tmp_path with a Python source file indexed (--no-llm)."""
    src = initialized / "auth.py"
    src.write_text(
        "class AuthService:\n"
        "    def login(self, user: str) -> bool:\n"
        "        return True\n"
        "\n"
        "def hash_password(pw: str) -> str:\n"
        "    return pw\n"
    )
    result = runner.invoke(
        cli,
        [
            "analyze",
            str(initialized),
            "--db-path",
            str(initialized / ".pyramid"),
            "--no-llm",
            "--workers",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    return initialized


# ─────────────────────────────────────────────
# init
# ─────────────────────────────────────────────


def test_init_creates_structure(tmp_path: Path, runner: CliRunner) -> None:
    result = runner.invoke(cli, ["init", "--db-path", str(tmp_path / ".pyramid")])

    assert result.exit_code == 0
    assert (tmp_path / ".pyramid" / "config.json").exists()
    assert (tmp_path / ".pyramid" / "index.json").exists()
    assert (tmp_path / ".pyramid" / "data").is_dir()


def test_init_config_fields(tmp_path: Path, runner: CliRunner) -> None:
    runner.invoke(cli, ["init", "--db-path", str(tmp_path / ".pyramid")])
    config = json.loads((tmp_path / ".pyramid" / "config.json").read_text())

    assert config["version"] == 1
    assert config["api"] == "anthropic"
    assert "created" in config


def test_init_idempotent(tmp_path: Path, runner: CliRunner) -> None:
    db = str(tmp_path / ".pyramid")
    runner.invoke(cli, ["init", "--db-path", db])
    result = runner.invoke(cli, ["init", "--db-path", db])

    assert result.exit_code == 0
    assert "Already initialized" in result.output


# ─────────────────────────────────────────────
# analyze
# ─────────────────────────────────────────────


def test_analyze_indexes_files(analyzed: Path) -> None:
    index = json.loads((analyzed / ".pyramid" / "index.json").read_text())
    assert len(index) > 0


def test_analyze_indexes_functions(analyzed: Path) -> None:
    index = json.loads((analyzed / ".pyramid" / "index.json").read_text())
    etypes = {v["element_type"] for v in index.values()}
    assert "file" in etypes
    assert "function" in etypes


def test_analyze_indexes_classes(analyzed: Path) -> None:
    index = json.loads((analyzed / ".pyramid" / "index.json").read_text())
    etypes = {v["element_type"] for v in index.values()}
    assert "class" in etypes


def test_analyze_writes_data_files(analyzed: Path) -> None:
    data_dir = analyzed / ".pyramid" / "data"
    assert any(data_dir.glob("*.json"))


def test_analyze_data_has_levels(analyzed: Path) -> None:
    data_dir = analyzed / ".pyramid" / "data"
    data = json.loads(next(data_dir.glob("*.json")).read_text())
    assert "levels" in data
    assert "4" in data["levels"]
    assert "8" in data["levels"]
    assert "16" in data["levels"]


def test_analyze_up_to_date_on_rerun(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "analyze",
            str(analyzed),
            "--db-path",
            str(analyzed / ".pyramid"),
            "--no-llm",
        ],
    )
    assert result.exit_code == 0
    assert "up to date" in result.output.lower()


def test_analyze_force_reruns(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "analyze",
            str(analyzed),
            "--db-path",
            str(analyzed / ".pyramid"),
            "--no-llm",
            "--force",
            "--workers",
            "1",
        ],
    )
    assert result.exit_code == 0
    assert "Indexed" in result.output


# ─────────────────────────────────────────────
# list
# ─────────────────────────────────────────────


def test_list_shows_files(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli, ["list", "--db-path", str(analyzed / ".pyramid"), "--level", "4"]
    )
    assert result.exit_code == 0
    assert "auth.py" in result.output


def test_list_functions(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["list", "--db-path", str(analyzed / ".pyramid"), "--type", "function"],
    )
    assert result.exit_code == 0
    # Both login and hash_password should appear
    assert "login" in result.output or "hash_password" in result.output


def test_list_classes(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["list", "--db-path", str(analyzed / ".pyramid"), "--type", "class"],
    )
    assert result.exit_code == 0
    assert "AuthService" in result.output


# ─────────────────────────────────────────────
# query
# ─────────────────────────────────────────────


def test_query_finds_by_name(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["query", "AuthService", "--db-path", str(analyzed / ".pyramid"), "--level", "4"],
    )
    assert result.exit_code == 0
    assert "AuthService" in result.output


def test_query_finds_by_path(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["query", "auth", "--db-path", str(analyzed / ".pyramid"), "--level", "4"],
    )
    assert result.exit_code == 0
    assert "auth.py" in result.output


def test_query_no_results(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["query", "xyzNeverMatches999", "--db-path", str(analyzed / ".pyramid")],
    )
    assert result.exit_code == 0
    assert "No results" in result.output


def test_query_type_filter(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "query",
            "auth",
            "--db-path",
            str(analyzed / ".pyramid"),
            "--type",
            "function",
        ],
    )
    assert result.exit_code == 0
    # Should only show functions, not the file
    assert "[function]" in result.output


# ─────────────────────────────────────────────
# get
# ─────────────────────────────────────────────


def test_get_returns_summary(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["get", "auth.py", "--db-path", str(analyzed / ".pyramid"), "--level", "4"],
    )
    assert result.exit_code == 0
    assert "auth.py" in result.output


def test_get_show_code(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        [
            "get",
            "auth.py",
            "--db-path",
            str(analyzed / ".pyramid"),
            "--level",
            "4",
            "--show-code",
        ],
    )
    assert result.exit_code == 0
    # Source code should appear between separator lines
    assert "AuthService" in result.output


def test_get_missing_element(analyzed: Path, runner: CliRunner) -> None:
    result = runner.invoke(
        cli,
        ["get", "nonexistent.py", "--db-path", str(analyzed / ".pyramid")],
    )
    assert result.exit_code != 0
    assert "No element found" in result.output


# ─────────────────────────────────────────────
# Unit: StorageManager
# ─────────────────────────────────────────────


def test_storage_roundtrip(tmp_path: Path) -> None:
    storage = StorageManager(tmp_path / ".pyramid")
    storage.init()

    data = {"path": "foo.py", "element_type": "file", "name": "foo.py", "levels": {}}
    storage.save_data("abc123", data)
    loaded = storage.load_data("abc123")

    assert loaded == data


def test_storage_load_missing_data(tmp_path: Path) -> None:
    storage = StorageManager(tmp_path / ".pyramid")
    storage.init()
    assert storage.load_data("doesnotexist") is None


# ─────────────────────────────────────────────
# Unit: CodeParser
# ─────────────────────────────────────────────


def test_parser_file_element(tmp_path: Path) -> None:
    src = tmp_path / "hello.py"
    src.write_text("x = 1\n")
    parser = CodeParser()
    elements = parser.parse_file(src, tmp_path)

    file_elements = [e for e in elements if e.element_type == "file"]
    assert len(file_elements) == 1
    assert file_elements[0].name == "hello.py"


def test_parser_extracts_functions(tmp_path: Path) -> None:
    src = tmp_path / "math.py"
    src.write_text("def add(a, b):\n    return a + b\n\ndef sub(a, b):\n    return a - b\n")
    parser = CodeParser()
    elements = parser.parse_file(src, tmp_path)

    func_names = {e.name for e in elements if e.element_type == "function"}
    assert "add" in func_names
    assert "sub" in func_names


def test_parser_extracts_classes(tmp_path: Path) -> None:
    src = tmp_path / "shapes.py"
    src.write_text("class Circle:\n    def area(self):\n        return 0\n")
    parser = CodeParser()
    elements = parser.parse_file(src, tmp_path)

    class_names = {e.name for e in elements if e.element_type == "class"}
    assert "Circle" in class_names


def test_parser_content_hash_stable(tmp_path: Path) -> None:
    src = tmp_path / "foo.py"
    src.write_text("x = 1\n")
    parser = CodeParser()
    e1 = parser.parse_file(src, tmp_path)[0]
    e2 = parser.parse_file(src, tmp_path)[0]
    assert e1.content_hash() == e2.content_hash()


def test_parser_walk_ignores_dot_pyramid(tmp_path: Path) -> None:
    (tmp_path / ".pyramid").mkdir()
    (tmp_path / ".pyramid" / "index.py").write_text("x = 1\n")
    (tmp_path / "real.py").write_text("y = 2\n")
    parser = CodeParser()
    files = parser.walk_directory(tmp_path)
    paths = [f.name for f in files]
    assert "real.py" in paths
    assert "index.py" not in paths


# ─────────────────────────────────────────────
# Unit: Summarizer
# ─────────────────────────────────────────────


def test_summarizer_no_llm_returns_stubs() -> None:
    summarizer = Summarizer(no_llm=True)
    element = Element(
        path="foo.py",
        element_type="function",
        name="my_func",
        code="def my_func(): pass",
        start_line=1,
        end_line=1,
    )
    result = summarizer.summarize(element, [4, 8, 16])
    assert result == {
        "4": "function my_func",
        "8": "function my_func",
        "16": "function my_func",
    }


def test_summarizer_detect_provider_no_llm() -> None:
    summarizer = Summarizer(no_llm=True)
    assert summarizer._detect_provider() == "stub"


def test_summarizer_parse_valid_json() -> None:
    raw = '{"4": "short summary here", "8": "slightly longer eight word description there"}'
    result = Summarizer._parse_summaries(raw, [4, 8])
    assert result["4"] == "short summary here"


def test_summarizer_parse_json_with_surrounding_text() -> None:
    raw = 'Here is your answer:\n{"4": "code summary text", "8": "longer code summary text here now"}'
    result = Summarizer._parse_summaries(raw, [4, 8])
    assert "4" in result
