from pathlib import Path

import pytest

from mindex.mindex import _db, add_file


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
        add_file(index_dir, test_file)

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
        add_file(index_dir, test_file, tag="test-tag")

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT tag FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()

        assert row["tag"] == "test-tag"

    def test_add_file_updates_existing(self, index_dir: Path, test_file: Path):
        """Test that add_file updates an existing entry."""
        # Add the file first time
        add_file(index_dir, test_file)

        # Modify the file
        test_file.write_text("# Updated Content\n\nNew content here.", encoding="utf-8")

        # Add again
        add_file(index_dir, test_file)

        with _db(index_dir) as conn:
            row = conn.execute(
                "SELECT content, size FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()

        assert row["content"] == "# Updated Content\n\nNew content here."
        assert row["size"] == len("# Updated Content\n\nNew content here.")

    def test_add_file_creates_fts_entry(self, index_dir: Path, test_file: Path):
        """Test that add_file also inserts into the FTS virtual table."""
        add_file(index_dir, test_file)

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
        add_file(index_dir, test_file)
        add_file(index_dir, test_file)

        with _db(index_dir) as conn:
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM docs WHERE path = ?",
                (str(test_file.absolute()),),
            ).fetchone()["cnt"]

        assert count == 1
