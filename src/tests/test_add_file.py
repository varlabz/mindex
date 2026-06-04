from pathlib import Path

import pytest

from mindex.cmd_add_file import add_file
from mindex.db import _db


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for the index."""
    return tmp_path


@pytest.fixture
def test_file(index_dir: Path) -> Path:
    """Create a temporary test file."""
    file_path = index_dir / "test.md"
    file_path.write_text("# Hello World\n\nThis is a test file.", encoding="utf-8")
    return file_path


class TestAddFile:
    def test_add_file_creates_entry(self, index_dir: Path, test_file: Path):
        """Test that add_file creates a database entry."""
        assert add_file(index_dir, test_file) == 1

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT path, content, size, hash, tag FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()

        assert row is not None
        assert row["path"] == str(test_file.absolute())
        assert row["content"] == "# Hello World\n\nThis is a test file."
        assert row["size"] == len("# Hello World\n\nThis is a test file.")
        assert row["hash"] is not None
        assert row["tag"] is None

    def test_add_file_with_tag(self, index_dir: Path, test_file: Path):
        """Test that add_file stores the tag correctly."""
        assert add_file(index_dir, test_file, tag="test-tag") == 1

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT tag FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()

        assert row["tag"] == "test-tag"

    def test_add_file_updates_existing(self, index_dir: Path, test_file: Path):
        """Test that add_file updates an existing entry."""
        # Add the file first time
        assert add_file(index_dir, test_file) == 1

        # Modify the file
        test_file.write_text("# Updated Content\n\nNew content here.", encoding="utf-8")

        # Add again — upserts, still returns 1
        assert add_file(index_dir, test_file) == 1

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT content, size FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()

        assert row["content"] == "# Updated Content\n\nNew content here."
        assert row["size"] == len("# Updated Content\n\nNew content here.")

    def test_add_file_creates_fts_entry(self, index_dir: Path, test_file: Path):
        """Test that add_file also inserts into the FTS virtual table."""
        assert add_file(index_dir, test_file) == 1

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT content FROM docs_fts WHERE content MATCH 'Hello World'"
            ).fetchone()

        assert row is not None

    def test_add_file_nonexistent_raises(self, index_dir: Path):
        """Test that add_file raises FileNotFoundError for a missing file."""
        missing = index_dir / "nonexistent.md"
        with pytest.raises(FileNotFoundError):
            add_file(index_dir, missing)

    def test_add_file_unique_path(self, index_dir: Path, test_file: Path):
        """Test that add_file does not create duplicate entries."""
        assert add_file(index_dir, test_file) == 1
        assert add_file(index_dir, test_file) == 1  # upsert, still returns 1

        with _db(index_dir) as conn:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()["cnt"]

        assert count == 1

    # ── Wildcard pattern tests ────────────────────────────────────────────

    def test_add_with_wildcard_star_matches_multiple(self, index_dir: Path):
        """Wildcard * indexes all matching files."""
        f1 = index_dir / "a.md"
        f1.write_text("content a", encoding="utf-8")
        f2 = index_dir / "b.md"
        f2.write_text("content b", encoding="utf-8")
        f3 = index_dir / "c.txt"
        f3.write_text("content c", encoding="utf-8")

        pattern = str(index_dir / "*.md")
        assert add_file(index_dir, pattern) == 2

        with _db(index_dir) as conn:
            rows = conn.execute("SELECT path FROM docs ORDER BY path").fetchall()
        assert len(rows) == 2
        assert rows[0]["path"].endswith("a.md")
        assert rows[1]["path"].endswith("b.md")

    def test_add_with_wildcard_question_mark(self, index_dir: Path):
        """Wildcard ? matches single characters."""
        f1 = index_dir / "ab.md"
        f1.write_text("ab", encoding="utf-8")
        f2 = index_dir / "ac.md"
        f2.write_text("ac", encoding="utf-8")
        f3 = index_dir / "abc.md"
        f3.write_text("abc", encoding="utf-8")

        pattern = str(index_dir / "a?.md")
        assert add_file(index_dir, pattern) == 2

        with _db(index_dir) as conn:
            paths = [r["path"] for r in conn.execute("SELECT path FROM docs").fetchall()]
        assert len(paths) == 2
        assert any(p.endswith("ab.md") for p in paths)
        assert any(p.endswith("ac.md") for p in paths)

    def test_add_with_wildcard_none_match_raises(self, index_dir: Path):
        """Wildcard matching zero files raises FileNotFoundError."""
        pattern = str(index_dir / "*.nonexistent")
        with pytest.raises(FileNotFoundError, match="No files matched pattern"):
            add_file(index_dir, pattern)

    def test_add_with_wildcard_partial_disk_match(self, index_dir: Path):
        """Wildcard matching some files on disk but some non-existent."""
        f1 = index_dir / "exists.md"
        f1.write_text("exists", encoding="utf-8")
        f2 = index_dir / "also.md"
        f2.write_text("also", encoding="utf-8")

        pattern = str(index_dir / "*.md")
        assert add_file(index_dir, pattern) == 2
