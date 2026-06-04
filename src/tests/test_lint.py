"""Tests for lint function."""

from pathlib import Path

import pytest

from mindex.mindex import LintInfo, add_file, del_file, lint


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for the index."""
    return tmp_path


@pytest.fixture
def file_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for the file root."""
    sub = tmp_path / "vault"
    sub.mkdir()
    return sub


@pytest.fixture
def indexed_files(index_dir: Path, file_dir: Path) -> dict[str, Path]:
    """Create and index multiple test files inside file_dir."""
    files = {}
    for name, content in [
        ("file1.md", "# File One\n\nContent one."),
        ("file2.md", "# File Two\n\nContent two."),
        ("sub/nested.md", "# Nested\n\nDeep content."),
    ]:
        file_path = file_dir / name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        add_file(index_dir, file_path)
        files[name] = file_path
    return files


# ── Positive Tests ─────────────────────────────────────────────────────


class TestLintPositive:
    """Positive test cases for lint."""

    def test_lint_returns_lint_info_list(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that lint returns a list of LintInfo."""
        results = lint(index_dir)
        assert len(results) == 3
        assert all(isinstance(r, LintInfo) for r in results)

    def test_lint_all_files_ok_when_exist(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that all indexed files show OK status when they exist on disk."""
        results = lint(index_dir)
        assert all(r.status == "OK" for r in results)

    def test_lint_correct_paths(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that lint returns correct file paths."""
        results = lint(index_dir)
        paths = {r.path for r in results}
        for name, path in indexed_files.items():
            assert str(path.absolute()) in paths

    def test_lint_with_file_dir_filters_files(
        self, indexed_files: dict[str, Path], index_dir: Path, file_dir: Path
    ):
        """Test that lint with file_dir returns only files under that directory."""
        # Create a file outside file_dir
        external = index_dir / "external.md"
        external.write_text("External file.", encoding="utf-8")
        add_file(index_dir, external)

        results = lint(index_dir, file_dir)
        for r in results:
            assert r.path.startswith(str(file_dir.absolute()))

    def test_lint_with_file_dir_excludes_external_files(
        self, indexed_files: dict[str, Path], index_dir: Path, file_dir: Path
    ):
        """Test that lint with file_dir excludes files outside the directory."""
        external = index_dir / "external.md"
        external.write_text("External file.", encoding="utf-8")
        add_file(index_dir, external)

        results = lint(index_dir, file_dir)
        for r in results:
            assert "external.md" not in r.path

    def test_lint_with_non_existent_file_dir(self, index_dir: Path):
        """Test that lint with a non-existent file_dir still works."""
        results = lint(index_dir, index_dir / "nonexistent")
        assert isinstance(results, list)

    def test_lint_with_file_dir_nested_files(
        self, indexed_files: dict[str, Path], index_dir: Path, file_dir: Path
    ):
        """Test that lint with file_dir includes nested files."""
        results = lint(index_dir, file_dir)
        nested_path = str((file_dir / "sub/nested.md").absolute())
        assert any(nested_path == r.path for r in results)


# ── Negative Tests ─────────────────────────────────────────────────────


class TestLintNegative:
    """Negative test cases for lint."""

    def test_lint_missing_files(self, index_dir: Path, file_dir: Path):
        """Test that lint reports missing files when they are deleted."""
        file_path = file_dir / "to_delete.md"
        file_path.write_text("To be deleted.", encoding="utf-8")
        add_file(index_dir, file_path)

        file_path.unlink()

        results = lint(index_dir)
        target = [r for r in results if r.path == str(file_path.absolute())]
        assert len(target) == 1
        assert target[0].status == "missing"

    def test_lint_empty_index(self, index_dir: Path):
        """Test that lint returns empty list when index has no files."""
        results = lint(index_dir)
        assert results == []

    def test_lint_with_file_dir_empty_index(self, index_dir: Path, file_dir: Path):
        """Test that lint with file_dir returns empty list when index is empty."""
        results = lint(index_dir, file_dir)
        assert results == []


# ── Edge Cases ─────────────────────────────────────────────────────────


class TestLintEdgeCases:
    """Edge case tests for lint."""

    def test_lint_file_with_special_chars_in_name(self, index_dir: Path, file_dir: Path):
        """Test lint on a file with special characters in its name."""
        file_path = file_dir / "test-file_v2.0 (draft).md"
        file_path.write_text("Special name content.", encoding="utf-8")
        add_file(index_dir, file_path)

        results = lint(index_dir)
        assert len(results) == 1
        assert results[0].status == "OK"
        assert results[0].path == str(file_path.absolute())

    def test_lint_file_with_unicode_content(self, index_dir: Path, file_dir: Path):
        """Test lint on a file with unicode content."""
        file_path = file_dir / "unicode.md"
        content = "こんにちは世界 🌍"
        file_path.write_text(content, encoding="utf-8")
        add_file(index_dir, file_path)

        results = lint(index_dir)
        assert len(results) == 1
        assert results[0].status == "OK"

    def test_lint_file_dir_with_trailing_slash_path(self, index_dir: Path, file_dir: Path):
        """Test lint works when file_dir path has no trailing slash."""
        file_path = file_dir / "test.md"
        file_path.write_text("Test content.", encoding="utf-8")
        add_file(index_dir, file_path)

        results = lint(index_dir, file_dir)
        assert len(results) == 1
        assert results[0].status == "OK"

    def test_lint_file_dir_subdirectory_only(self, index_dir: Path, file_dir: Path):
        """Test lint with file_dir set to a subdirectory."""
        sub = file_dir / "sub"
        sub.mkdir()

        inside = sub / "inside.md"
        inside.write_text("Inside sub.", encoding="utf-8")
        add_file(index_dir, inside)

        outside = file_dir / "outside.md"
        outside.write_text("Outside sub.", encoding="utf-8")
        add_file(index_dir, outside)

        results = lint(index_dir, sub)
        paths = {r.path for r in results}
        assert str(inside.absolute()) in paths
        assert str(outside.absolute()) not in paths

    def test_lint_same_file_added_twice(self, index_dir: Path, file_dir: Path):
        """Test lint when the same file is indexed twice."""
        file_path = file_dir / "duplicate.md"
        file_path.write_text("Duplicate test.", encoding="utf-8")
        add_file(index_dir, file_path)
        add_file(index_dir, file_path)

        results = lint(index_dir)
        matching = [r for r in results if "duplicate.md" in r.path]
        assert len(matching) == 1
        assert matching[0].status == "OK"

    def test_lint_large_number_of_files(self, index_dir: Path, file_dir: Path):
        """Test lint with a large number of indexed files."""
        for i in range(100):
            file_path = file_dir / f"file_{i:03d}.md"
            file_path.write_text(f"Content {i}", encoding="utf-8")
            add_file(index_dir, file_path)

        results = lint(index_dir)
        assert len(results) == 100
        assert all(r.status == "OK" for r in results)

    def test_lint_deleted_file_not_counted_twice(self, index_dir: Path, file_dir: Path):
        """Test that a deleted file is not counted multiple times."""
        file_path = file_dir / "deleted.md"
        file_path.write_text("Will be deleted.", encoding="utf-8")
        add_file(index_dir, file_path)
        file_path.unlink()

        results = lint(index_dir)
        missing = [r for r in results if r.path == str(file_path.absolute())]
        assert len(missing) == 1
        assert missing[0].status == "missing"
