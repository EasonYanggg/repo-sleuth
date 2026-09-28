from pathlib import Path

import pytest

from app.repository import Repository, RepositoryError


def test_read_stays_inside_repository(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "inside.py").write_text("ok", encoding="utf-8")
    (tmp_path / "secret.txt").write_text("secret", encoding="utf-8")
    (repo_dir / "link.txt").symlink_to(tmp_path / "secret.txt")
    repo = Repository(str(repo_dir))
    assert repo.read_file("inside.py") == "1 | ok"
    for path in ("../secret.txt", "link.txt"):
        with pytest.raises(RepositoryError):
            repo.read_file(path)


def test_literal_search_is_not_shell(tmp_path: Path):
    (tmp_path / "sample.py").write_text("value = '$(touch pwned)'", encoding="utf-8")
    repo = Repository(str(tmp_path))
    assert "sample.py:1" in repo.search_code("$(touch pwned)")
    assert not (tmp_path / "pwned").exists()


def test_secret_files_are_not_exposed(tmp_path: Path):
    (tmp_path / ".env").write_text("API_KEY=private", encoding="utf-8")
    (tmp_path / "app.py").write_text("visible = True", encoding="utf-8")
    (tmp_path / "alias.py").symlink_to(tmp_path / ".env")
    repo = Repository(str(tmp_path))
    assert ".env" not in repo.list_files()
    assert "API_KEY=private" not in repo.search_code("API_KEY")
    for path in (".env", "alias.py"):
        with pytest.raises(RepositoryError):
            repo.read_file(path)
