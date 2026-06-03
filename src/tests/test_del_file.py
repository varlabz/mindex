"""Tests for del_file function — positive, negative, and edge cases."""

import pytest
from pathlib import Path
from mindex import add_file, del_file, _db


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_index(tmp_path: Path):
    """Create a temporary index directory."""
    index_dir = tmp_path / "index"
    index_dir.mkdir()
    return index_dir, tmp_path


# ── Helpers ──────────────────────────────────────────────────────────────────

def _count_docs(index_dir: Path) -> int:
    with _db(index_dir) as conn:
        return conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]


def _count_fts(index_dir: Path) -> int:
    with _db(index_dir) as conn:
        return conn.execute("SELECT COUNT(*) FROM docs_fts").fetchone()[0]


def _create_file(tmp_path: Path, name: str, content: str) -> Path:
    f = tmp_path / name
    f.write_text(content, encoding="utf-8")
    return f


# ── Positive tests: del_file SHOULD succeed and produce correct state ────────

class TestDelFilePositive:
    """Expected-success scenarios."""

    def test_del_removes_single_file_from_docs(self, tmp_index):
        """Positive: deleting an indexed file removes it from docs."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "hello world")
        add_file(index_dir, f)
        assert _count_docs(index_dir) == 1

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_removes_single_file_from_fts(self, tmp_index):
        """Positive: deleting an indexed file removes it from FTS."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "hello world")
        add_file(index_dir, f)
        assert _count_fts(index_dir) == 1

        del_file(index_dir, f)
        assert _count_fts(index_dir) == 0

    def test_del_after_file_update(self, tmp_index):
        """Positive: deleting a file that was updated still works."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "v1")
        add_file(index_dir, f)
        f.write_text("v2", encoding="utf-8")
        add_file(index_dir, f)
        assert _count_docs(index_dir) == 1

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_with_tag(self, tmp_index):
        """Positive: deleting a tagged file removes it completely."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "tagged content")
        add_file(index_dir, f, tag="mytag")
        assert _count_docs(index_dir) == 1

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_one_of_many_does_not_affect_others(self, tmp_index):
        """Positive: deleting one file leaves others intact."""
        index_dir, tmp_path = tmp_index
        f1 = _create_file(tmp_path, "a.md", "content a")
        f2 = _create_file(tmp_path, "b.md", "content b")
        f3 = _create_file(tmp_path, "c.md", "content c")
        add_file(index_dir, f1)
        add_file(index_dir, f2)
        add_file(index_dir, f3)
        assert _count_docs(index_dir) == 3

        del_file(index_dir, f2)
        assert _count_docs(index_dir) == 2

    def test_del_multiple_times_only_first_removes(self, tmp_index):
        """Positive: calling del_file twice does not error; second call is a no-op."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "content")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

        # Second delete should not raise
        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_with_empty_content(self, tmp_index):
        """Positive: deleting a file with empty content works."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "empty.md", "")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_with_unicode_content(self, tmp_index):
        """Positive: deleting a file with unicode content works."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "unicode.md", "こんにちは 🌍 café")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_with_large_content(self, tmp_index):
        """Positive: deleting a large file works."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "large.md", "x" * 1_000_000)
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_all_files_leaves_empty_index(self, tmp_index):
        """Positive: deleting all files leaves an empty but valid index."""
        index_dir, tmp_path = tmp_index
        files = [_create_file(tmp_path, f"{i}.md", f"content {i}") for i in range(5)]
        for f in files:
            add_file(index_dir, f)
        assert _count_docs(index_dir) == 5

        for f in files:
            del_file(index_dir, f)
        assert _count_docs(index_dir) == 0
        assert _count_fts(index_dir) == 0


# ── Negative tests: things that should NOT happen or should fail gracefully ──

class TestDelFileNegative:
    """Expected-no-op or mismatch scenarios."""

    def test_del_nonexistent_file_does_nothing(self, tmp_index):
        """Negative: deleting a file that was never added does not error
        and does not change state."""
        index_dir, tmp_path = tmp_index
        f = tmp_path / "never_added.md"

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_with_relative_path_does_not_match_absolute(self, tmp_index):
        """Negative: relative path does not match stored absolute path — file remains indexed."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "content")
        add_file(index_dir, f)
        assert _count_docs(index_dir) == 1

        # Relative path — should NOT match
        del_file(index_dir, Path("a.md"))
        assert _count_docs(index_dir) == 1

    def test_del_with_different_absolute_path_does_not_match(self, tmp_index):
        """Negative: different absolute path does not match — file remains indexed."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "content")
        add_file(index_dir, f)
        assert _count_docs(index_dir) == 1

        # Different path — should NOT match
        fake = tmp_path / "other" / "a.md"
        del_file(index_dir, fake)
        assert _count_docs(index_dir) == 1

    def test_del_does_not_affect_other_files_with_similar_names(self, tmp_index):
        """Negative: deleting one file does not affect files with similar names."""
        index_dir, tmp_path = tmp_index
        f1 = _create_file(tmp_path, "test.md", "content 1")
        f2 = _create_file(tmp_path, "test_backup.md", "content 2")
        f3 = _create_file(tmp_path, "my_test.md", "content 3")
        add_file(index_dir, f1)
        add_file(index_dir, f2)
        add_file(index_dir, f3)
        assert _count_docs(index_dir) == 3

        del_file(index_dir, f1)
        assert _count_docs(index_dir) == 2

    def test_del_does_not_clear_fts_for_other_files(self, tmp_index):
        """Negative: deleting one file does not remove other files from FTS."""
        index_dir, tmp_path = tmp_index
        f1 = _create_file(tmp_path, "a.md", "unique word alpha")
        f2 = _create_file(tmp_path, "b.md", "unique word beta")
        add_file(index_dir, f1)
        add_file(index_dir, f2)
        assert _count_fts(index_dir) == 2

        del_file(index_dir, f1)
        assert _count_fts(index_dir) == 1


# ── Edge case tests ─────────────────────────────────────────────────────────

class TestDelFileEdgeCases:
    """Boundary conditions and unusual inputs."""

    def test_del_file_path_with_special_characters(self, tmp_index):
        """Edge: file path contains special characters."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "file [v2.0] (test).md", "content")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_file_path_with_spaces(self, tmp_index):
        """Edge: file path contains spaces."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "my file name.md", "content")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_file_in_nested_directory(self, tmp_index):
        """Edge: file is in a deeply nested directory."""
        index_dir, tmp_path = tmp_index
        nested = tmp_path / "a" / "b" / "c" / "d"
        nested.mkdir(parents=True)
        f = _create_file(nested, "deep.md", "deep content")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_file_with_null_byte_in_content(self, tmp_index):
        """Edge: file content contains null byte."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "null.md", "content\x00here")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_file_with_newlines_and_whitespace(self, tmp_index):
        """Edge: file content is only whitespace and newlines."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "whitespace.md", "\n\n   \t\t  \n\n")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_file_preserves_index_structure(self, tmp_index):
        """Edge: after deletion the index tables still exist and are queryable."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "content")
        add_file(index_dir, f)
        del_file(index_dir, f)

        # Tables should still exist
        with _db(index_dir) as conn:
            tables = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
            table_names = [t["name"] for t in tables]
        assert "docs" in table_names
        assert "docs_fts" in table_names

    def test_del_file_concurrent_add_and_delete(self, tmp_index):
        """Edge: adding and deleting the same file in sequence."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "v1")

        add_file(index_dir, f)
        assert _count_docs(index_dir) == 1

        f.write_text("v2", encoding="utf-8")
        add_file(index_dir, f)
        assert _count_docs(index_dir) == 1

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_file_path_is_symlink(self, tmp_index):
        """Edge: file is a symlink (del_file should still work via absolute path)."""
        index_dir, tmp_path = tmp_index
        real_file = _create_file(tmp_path, "real.md", "symlink target")
        link = tmp_path / "link.md"
        link.symlink_to(real_file)
        add_file(index_dir, link)

        del_file(index_dir, link)
        assert _count_docs(index_dir) == 0

    def test_del_file_with_dotfile_name(self, tmp_index):
        """Edge: file with dotfile name."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, ".hidden.md", "dotfile content")
        add_file(index_dir, f)

        del_file(index_dir, f)
        assert _count_docs(index_dir) == 0

    def test_del_file_does_not_affect_hash_or_metadata(self, tmp_index):
        """Edge: verify del_file removes the row entirely, not just content."""
        index_dir, tmp_path = tmp_index
        f = _create_file(tmp_path, "a.md", "content")
        add_file(index_dir, f)

        # Verify hash exists before delete
        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT hash, tag FROM docs WHERE path = ?", (str(f.absolute()),)
            ).fetchone()
        assert row is not None
        assert row["hash"] is not None

        del_file(index_dir, f)

        # Row should be completely gone
        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM docs WHERE path = ?", (str(f.absolute()),)
            ).fetchone()
        assert row[0] == 0
