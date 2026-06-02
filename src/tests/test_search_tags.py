#!/usr/bin/env python3
"""
Test that search returns tags associated with documents.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from mindex import add_file, search


@pytest.fixture
def temp_index_dir():
    """Create a temporary directory for test index."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def temp_markdown_files():
    """Create temporary markdown files for testing."""
    temp_dir = tempfile.mkdtemp()
    
    file1 = Path(temp_dir) / "agent.md"
    file1.write_text("# Agent Memory\nAI agents need persistent memory.")
    
    file2 = Path(temp_dir) / "database.md"
    file2.write_text("# Database Guide\nSQLite with FTS5 for search.")
    
    yield temp_dir, file1, file2
    shutil.rmtree(temp_dir)


def test_search_returns_tags(temp_index_dir, temp_markdown_files):
    """Search results should include tags for documents that have them."""
    temp_dir, file1, file2 = temp_markdown_files
    index_path = Path(temp_index_dir)
    
    # Add files with tags
    add_file(file1, index_path, title="Agent Memory", summary="AI memory", tags=["ai", "memory", "agents"])
    add_file(file2, index_path, title="Database Guide", summary="Database", tags=["database", "sqlite", "search"])
    
    # Search
    results = search("memory", index_path)
    
    assert results is not None
    assert len(results) > 0
    
    # Check tags are present
    result = results[0]
    assert "tags" in dict(result)
    tags = result["tags"]
    assert tags is not None
    
    # Tags should be comma-separated string
    assert "ai" in tags
    assert "memory" in tags
    assert "agents" in tags


def test_search_returns_empty_tags(temp_index_dir, temp_markdown_files):
    """Search results should handle documents without tags."""
    temp_dir, file1, file2 = temp_markdown_files
    index_path = Path(temp_index_dir)
    
    # Add file without tags
    add_file(file1, index_path, title="Agent Memory", summary="AI memory")
    
    # Search
    results = search("memory", index_path)
    
    assert results is not None
    assert len(results) > 0
    
    result = results[0]
    assert "tags" in dict(result)
    # Tags should be empty list for documents without tags
    assert result["tags"] == []


def test_search_multiple_docs_with_different_tags(temp_index_dir, temp_markdown_files):
    """Search multiple documents and verify each has correct tags."""
    temp_dir, file1, file2 = temp_markdown_files
    index_path = Path(temp_index_dir)
    
    # Add files with different tags
    add_file(file1, index_path, title="Agent Memory", summary="AI systems memory", tags=["ai", "memory"])
    add_file(file2, index_path, title="Database Guide", summary="Database systems", tags=["database"])
    
    # Search for common term
    results = search("systems", index_path)
    
    assert results is not None
    assert len(results) == 2
    
    # Check each result has its own tags
    tags_by_title = {r["title"]: r["tags"] for r in results}
    
    assert "ai" in tags_by_title["Agent Memory"]
    assert "memory" in tags_by_title["Agent Memory"]
    assert "database" in tags_by_title["Database Guide"]
