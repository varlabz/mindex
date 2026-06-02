#!/usr/bin/env python3
"""
Tests for mindex CLI error handling.
"""

import pytest
import tempfile
import shutil
import subprocess
import sys
from pathlib import Path


@pytest.fixture
def temp_index_dir():
    """Create a temporary directory for test index."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_markdown_file():
    """Create a temporary markdown file."""
    temp_dir = tempfile.mkdtemp()
    file = Path(temp_dir) / "test.md"
    file.write_text("# Test\nTest content.")
    yield temp_dir, file
    shutil.rmtree(temp_dir)


def run_cli(*args):
    """Run mindex CLI and return result."""
    result = subprocess.run(
        [sys.executable, "-m", "mindex.mindex"] + list(args),
        capture_output=True,
        text=True
    )
    return result


class TestCLIErrors:
    """Test CLI error handling."""
    
    def test_add_missing_title(self, temp_index_dir, temp_markdown_file):
        """Add command without --title should fail."""
        _, file = temp_markdown_file
        result = run_cli("--index", temp_index_dir, "add", str(file), "--summary", "Test")
        assert result.returncode != 0
    
    def test_add_missing_summary(self, temp_index_dir, temp_markdown_file):
        """Add command without --summary should fail."""
        _, file = temp_markdown_file
        result = run_cli("--index", temp_index_dir, "add", str(file), "--title", "Test")
        assert result.returncode != 0
    
    def test_add_nonexistent_file(self, temp_index_dir):
        """Add command with nonexistent file should fail."""
        result = run_cli("--index", temp_index_dir, "add", "/nonexistent/file.md", 
                        "--title", "Test", "--summary", "Test")
        assert result.returncode != 0
        assert "Not found" in result.stderr or "Error" in result.stderr
    
    def test_search_empty_index(self, temp_index_dir):
        """Search on empty index should fail."""
        result = run_cli("--index", temp_index_dir, "search", "test")
        assert result.returncode != 0
        assert "Index is empty" in result.stderr or "Error" in result.stderr
    
    def test_info_nonexistent_file(self, temp_index_dir):
        """Info command for nonexistent file should fail."""
        result = run_cli("--index", temp_index_dir, "info", "/nonexistent/file.md")
        assert result.returncode != 0
        assert "Not found" in result.stderr or "Error" in result.stderr
    
    def test_info_unindexed_file(self, temp_index_dir, temp_markdown_file):
        """Info command for unindexed file should fail."""
        _, file = temp_markdown_file
        result = run_cli("--index", temp_index_dir, "info", str(file))
        assert result.returncode != 0
        assert "not indexed" in result.stderr or "Error" in result.stderr
    
    def test_delete_nonexistent_file(self, temp_index_dir):
        """Delete command for nonexistent file should fail."""
        result = run_cli("--index", temp_index_dir, "rm", "/nonexistent/file.md")
        assert result.returncode != 0
        assert "Not found" in result.stderr or "Error" in result.stderr
    
    def test_delete_unindexed_file(self, temp_index_dir, temp_markdown_file):
        """Delete command for unindexed file should fail."""
        _, file = temp_markdown_file
        result = run_cli("--index", temp_index_dir, "rm", str(file))
        assert result.returncode != 0
        assert "not indexed" in result.stderr or "Error" in result.stderr
    
    def test_show_nonexistent_file(self, temp_index_dir):
        """Show command for nonexistent file should fail."""
        result = run_cli("--index", temp_index_dir, "show", "/nonexistent/file.md")
        assert result.returncode != 0
        assert "Not found" in result.stderr or "Error" in result.stderr
    
    def test_show_unindexed_file(self, temp_index_dir, temp_markdown_file):
        """Show command for unindexed file should fail."""
        _, file = temp_markdown_file
        result = run_cli("--index", temp_index_dir, "show", str(file))
        assert result.returncode != 0
        assert "not indexed" in result.stderr or "Error" in result.stderr
