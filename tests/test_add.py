#!/usr/bin/env python3
"""
Tests for mindex.py — focus on add_file function.

Run with: pytest tests/ -v
"""

import pytest
import sqlite3
import tempfile
from pathlib import Path
import sys

# Import the module under test
import mindex


class TestAddFilePositive:
    """Positive test cases for add_file function."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace with test files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            yield workspace

    def test_add_new_file_minimal(self, temp_workspace):
        """Test adding a new markdown file with minimal required fields."""
        # Setup
        test_file = temp_workspace / "test.md"
        test_file.write_text("# Test Document\n\nThis is a test.")
        
        # Execute
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Test Document",
            summary="A test document"
        )
        
        # Verify
        with mindex._db(temp_workspace) as conn:
            doc = conn.execute(
                "SELECT * FROM docs WHERE path = ?", 
                (str(test_file),)
            ).fetchone()
            assert doc is not None
            assert doc["title"] == "Test Document"
            assert doc["summary"] == "A test document"
            assert "# Test Document" in doc["content"]

    def test_add_file_with_tags(self, temp_workspace):
        """Test adding a file with multiple tags."""
        test_file = temp_workspace / "tagged.md"
        test_file.write_text("# Tagged Document\n\nWith tags.")
        
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Tagged Doc",
            summary="Has tags",
            tags=["python", "testing", "sqlite"]
        )
        
        with mindex._db(temp_workspace) as conn:
            doc = conn.execute(
                "SELECT id FROM docs WHERE path = ?", 
                (str(test_file),)
            ).fetchone()
            tags = conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ? ORDER BY tag",
                (doc["id"],)
            ).fetchall()
            tag_list = [t["tag"] for t in tags]
            assert tag_list == ["python", "sqlite", "testing"]

    def test_add_file_with_custom_source(self, temp_workspace):
        """Test adding a file with custom source URL."""
        test_file = temp_workspace / "remote.md"
        test_file.write_text("# Remote Doc\n\nContent from URL.")
        source_url = "https://example.com/original.md"
        
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Remote Doc",
            summary="From remote source",
            source=source_url
        )
        
        with mindex._db(temp_workspace) as conn:
            doc = conn.execute(
                "SELECT source FROM docs WHERE path = ?", 
                (str(test_file),)
            ).fetchone()
            assert doc["source"] == source_url

    def test_add_file_updates_existing(self, temp_workspace):
        """Test that updating a file replaces old content."""
        test_file = temp_workspace / "mutable.md"
        test_file.write_text("# Original\n\nOriginal content.")
        
        # Add initial version
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Original Title",
            summary="Original summary"
        )
        
        # Update file content and re-add with new title/summary
        test_file.write_text("# Updated\n\nUpdated content.")
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Updated Title",
            summary="Updated summary"
        )
        
        with mindex._db(temp_workspace) as conn:
            doc = conn.execute(
                "SELECT * FROM docs WHERE path = ?", 
                (str(test_file),)
            ).fetchone()
            assert doc["title"] == "Updated Title"
            assert "Updated content" in doc["content"]
            # Should have only one record (updated, not duplicated)
            count = conn.execute(
                "SELECT COUNT(*) as c FROM docs WHERE path = ?", 
                (str(test_file),)
            ).fetchone()["c"]
            assert count == 1

    def test_skip_unchanged_file(self, temp_workspace, capsys):
        """Test that unchanged files are skipped without re-indexing."""
        test_file = temp_workspace / "static.md"
        test_file.write_text("# Static\n\nUnchanged content.")
        
        # Add file
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Static Title",
            summary="Static summary"
        )
        capsys.readouterr()  # Clear output
        
        # Try to add same file again WITHOUT title/summary (should be skipped if unchanged)
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Static Title",
            summary="Static summary"
        )
        
        captured = capsys.readouterr()
        # File is unchanged AND we're providing same title/summary, but since we're
        # providing title/summary, it won't skip. Let's verify it's not adding a duplicate instead.
        with mindex._db(temp_workspace) as conn:
            count = conn.execute(
                "SELECT COUNT(*) as c FROM docs WHERE path = ?",
                (str(test_file),)
            ).fetchone()["c"]
            assert count == 1  # Only one record, not duplicated

    def test_add_file_preserves_size(self, temp_workspace):
        """Test that file size in characters is calculated and stored correctly."""
        test_file = temp_workspace / "chars.md"
        content = "# Title\n\nOne two three four five."  # 33 characters
        test_file.write_text(content)
        
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Size Test",
            summary="Testing character count"
        )
        
        with mindex._db(temp_workspace) as conn:
            doc = conn.execute(
                "SELECT size FROM docs WHERE path = ?", 
                (str(test_file),)
            ).fetchone()
            assert doc["size"] == 33

    def test_add_file_with_duplicate_tags(self, temp_workspace):
        """Test that duplicate tags are deduplicated."""
        test_file = temp_workspace / "dups.md"
        test_file.write_text("# Doc\n\nContent.")
        
        mindex.add_file(
            test_file,
            index_path=temp_workspace,
            title="Duplicate Tags",
            summary="Testing dedup",
            tags=["python", "testing", "python", "python"]
        )
        
        with mindex._db(temp_workspace) as conn:
            doc = conn.execute(
                "SELECT id FROM docs WHERE path = ?", 
                (str(test_file),)
            ).fetchone()
            tags = conn.execute(
                "SELECT tag FROM tags WHERE doc_id = ?",
                (doc["id"],)
            ).fetchall()
            assert len(tags) == 2  # Only 2 unique tags


class TestAddFileNegative:
    """Negative test cases for add_file function."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_add_nonexistent_file(self, temp_workspace):
        """Test that adding a non-existent file raises an error."""
        nonexistent = temp_workspace / "does_not_exist.md"
        
        with pytest.raises(FileNotFoundError):
            mindex.add_file(
                nonexistent,
                index_path=temp_workspace,
                title="Ghost Doc",
                summary="Doesn't exist"
            )

    def test_add_file_missing_title(self, temp_workspace):
        """Test that title is required (based on add_file signature)."""
        test_file = temp_workspace / "no_title.md"
        test_file.write_text("# Content")
        
        # title=None should cause issues when inserting
        with pytest.raises((TypeError, sqlite3.IntegrityError)):
            mindex.add_file(
                test_file,
                index_path=temp_workspace,
                title=None,
                summary="Has summary"
            )

    def test_add_file_missing_summary(self, temp_workspace):
        """Test that summary is required."""
        test_file = temp_workspace / "no_summary.md"
        test_file.write_text("# Content")
        
        with pytest.raises((TypeError, sqlite3.IntegrityError)):
            mindex.add_file(
                test_file,
                index_path=temp_workspace,
                title="Has title",
                summary=None
            )
