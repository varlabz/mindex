#!/usr/bin/env python3
"""
CLI tests for mindex.py command-line interface.

Run with: pytest tests/test_cli_complete.py -v
"""

import pytest
import tempfile
import shutil
import subprocess
import json
from pathlib import Path


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace with test files and index."""
    temp_dir = tempfile.mkdtemp()
    workspace = Path(temp_dir)
    
    # Create test markdown files
    (workspace / "python.md").write_text("# Python Guide\nPython programming language.")
    (workspace / "sqlite.md").write_text("# SQLite Database\nSQLite full-text search.")
    (workspace / "tutorial.md").write_text("# Tutorial\nPython and SQLite tutorial.")
    
    yield workspace
    shutil.rmtree(temp_dir)


class TestCLIAdd:
    """Test CLI add command."""

    def test_add_file_basic(self, temp_workspace):
        """Test adding a file with basic metadata."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python Guide",
                "--summary", "Python programming guide"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_add_file_with_comma_separated_tags(self, temp_workspace):
        """Test adding a file with comma-separated tags."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python Guide",
                "--summary", "Guide",
                "--tags", "python,programming,tutorial"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_add_file_with_space_separated_tags(self, temp_workspace):
        """Test adding a file with space-separated tags."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "sqlite.md"),
                "--title", "SQLite Guide",
                "--summary", "Database guide",
                "--tags", "sqlite", "database", "fts5"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0

    def test_add_file_with_custom_source(self, temp_workspace):
        """Test adding a file with custom source URL."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "tutorial.md"),
                "--title", "Tutorial",
                "--summary", "Complete tutorial",
                "--source", "https://example.com/tutorial"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0


class TestCLISearch:
    """Test CLI search command."""

    @pytest.fixture
    def indexed_workspace(self, temp_workspace):
        """Create workspace with indexed files."""
        # Add files to index
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python Guide",
                "--summary", "Python programming",
                "--tags", "python,programming"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "sqlite.md"),
                "--title", "SQLite Database",
                "--summary", "Database guide",
                "--tags", "sqlite,database"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "tutorial.md"),
                "--title", "Tutorial",
                "--summary", "Python and SQLite",
                "--tags", "python,sqlite,tutorial"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        return temp_workspace

    def test_search_basic(self, indexed_workspace):
        """Test basic search without filters."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(indexed_workspace),
                "search", "guide"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert len(output) >= 1

    def test_search_with_single_tag(self, indexed_workspace):
        """Test search with single tag filter."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(indexed_workspace),
                "search", "guide",
                "--tags", "python"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert len(output) >= 1
        for result_item in output:
            assert "python" in result_item["tags"]

    def test_search_with_comma_separated_tags(self, indexed_workspace):
        """Test search with comma-separated tags."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(indexed_workspace),
                "search", "tutorial",
                "--tags", "python,sqlite"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert len(output) == 1
        assert output[0]["title"] == "Tutorial"
        assert "python" in output[0]["tags"]
        assert "sqlite" in output[0]["tags"]

    def test_search_with_space_separated_tags(self, indexed_workspace):
        """Test search with space-separated tags."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(indexed_workspace),
                "search", "tutorial",
                "--tags", "python", "sqlite"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert len(output) == 1
        assert "python" in output[0]["tags"]
        assert "sqlite" in output[0]["tags"]

    def test_search_with_limit(self, indexed_workspace):
        """Test search with result limit."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(indexed_workspace),
                "search", "guide",
                "--limit", "1"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert len(output) <= 1

    def test_search_text_output(self, indexed_workspace):
        """Test search with text output format."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(indexed_workspace),
                "search", "guide",
                "--text"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "path:" in result.stdout
        assert "title:" in result.stdout

    def test_search_specific_file(self, indexed_workspace):
        """Test search within specific file."""
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(indexed_workspace),
                "search", "programming",
                "--file", str(indexed_workspace / "python.md")
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert len(output) >= 1
        assert all(str(indexed_workspace / "python.md") in r["path"] for r in output)


class TestCLITags:
    """Test CLI tags command."""

    def test_tags_list(self, temp_workspace):
        """Test listing all tags."""
        # Add files with tags
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python",
                "--summary", "Guide",
                "--tags", "python,programming"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "sqlite.md"),
                "--title", "SQLite",
                "--summary", "Database",
                "--tags", "sqlite,database"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        # List tags
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "tags"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        tags = result.stdout.strip().split("\n")
        assert "python" in tags
        assert "sqlite" in tags
        assert "programming" in tags
        assert "database" in tags


class TestCLIInfo:
    """Test CLI info command."""

    def test_info_basic(self, temp_workspace):
        """Test getting file info."""
        # Add file
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python Guide",
                "--summary", "Programming guide",
                "--tags", "python,programming"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        # Get info (JSON output is default)
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "info", str(temp_workspace / "python.md")
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        info = json.loads(result.stdout)
        assert info["title"] == "Python Guide"
        assert info["summary"] == "Programming guide"
        assert "python" in info["tags"]

    def test_info_text_output(self, temp_workspace):
        """Test getting file info in text format."""
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python Guide",
                "--summary", "Guide",
                "--tags", "python"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "info", str(temp_workspace / "python.md"),
                "--text"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Python Guide" in result.stdout
        assert "python" in result.stdout


class TestCLIDelete:
    """Test CLI delete/rm command."""

    def test_delete_file(self, temp_workspace):
        """Test deleting a file from index."""
        # Add file
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python",
                "--summary", "Guide"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        # Delete file
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "rm", str(temp_workspace / "python.md")
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        
        # Verify file is deleted (info should fail)
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "info", str(temp_workspace / "python.md")
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode != 0


class TestCLIRead:
    """Test CLI read command."""

    def test_read_full_content(self, temp_workspace):
        """Test reading full file content."""
        # Add file
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python",
                "--summary", "Guide"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        # Read file
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "read", str(temp_workspace / "python.md")
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert "Python Guide" in result.stdout

    def test_read_with_position_and_size(self, temp_workspace):
        """Test reading file with position and size limits."""
        subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "add", str(temp_workspace / "python.md"),
                "--title", "Python",
                "--summary", "Guide"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True
        )
        
        result = subprocess.run(
            [
                "uv", "run", "src/mindex/mindex.py",
                "--index", str(temp_workspace),
                "read", str(temp_workspace / "python.md"),
                "--position", "0",
                "--size", "10"
            ],
            cwd="/Users/varis/Workspaces/docs",
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        assert len(result.stdout) <= 11  # 10 chars + newline
