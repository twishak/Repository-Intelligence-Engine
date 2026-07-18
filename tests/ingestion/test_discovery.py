import subprocess

from codebase_agent.ingestion.discovery import (
    discover_files,
    git_index_has_zero_tracked_files,
)


def _git_init(repo_path):
    subprocess.run(["git", "init", "-q"], cwd=repo_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=repo_path, check=True)


def test_discovers_tracked_python_files(tmp_path):
    (tmp_path / "main.py").write_text("def main():\n    pass\n", encoding="utf-8")
    (tmp_path / "README.md").write_text("# hello\n", encoding="utf-8")
    _git_init(tmp_path)

    sources = discover_files(tmp_path)

    assert [s.path for s in sources] == ["main.py"]
    assert sources[0].language == "python"
    assert sources[0].line_count == 2


def test_ignores_oversized_file(tmp_path):
    (tmp_path / "small.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "huge.py").write_text("x = 1\n" * 200_000, encoding="utf-8")
    _git_init(tmp_path)

    sources = discover_files(tmp_path)

    assert [s.path for s in sources] == ["small.py"]


def test_ignores_binary_file(tmp_path):
    (tmp_path / "ok.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "bad.py").write_bytes(b"\x00\x01\x02")
    _git_init(tmp_path)

    sources = discover_files(tmp_path)

    assert [s.path for s in sources] == ["ok.py"]


def test_falls_back_to_walk_when_not_a_git_repo(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "__pycache__" / "main.cpython-311.pyc").write_bytes(b"\x00\x01")

    sources = discover_files(tmp_path)

    assert [s.path for s in sources] == ["main.py"]


def test_falls_back_to_walk_when_git_index_is_empty(tmp_path):
    # A repo directory can look like a valid git repo (has a .git dir) while
    # its index tracks nothing - e.g. a clone whose checkout step failed
    # partway (long paths on Windows) but left files on disk regardless.
    # `git ls-files` succeeds and returns nothing in this case, which must
    # not be treated the same as "no in-scope files exist".
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

    sources = discover_files(tmp_path)

    assert [s.path for s in sources] == ["main.py"]


def test_git_index_has_zero_tracked_files_true_when_index_empty(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

    assert git_index_has_zero_tracked_files(tmp_path) is True


def test_git_index_has_zero_tracked_files_false_when_files_tracked(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")
    _git_init(tmp_path)

    assert git_index_has_zero_tracked_files(tmp_path) is False


def test_git_index_has_zero_tracked_files_false_when_not_a_git_repo(tmp_path):
    (tmp_path / "main.py").write_text("x = 1\n", encoding="utf-8")

    assert git_index_has_zero_tracked_files(tmp_path) is False
