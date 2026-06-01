#!/usr/bin/env python3
"""
Tests for mindex search functionality.
Covers positive and negative test cases.
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from mindex import add_file, search, _db


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
    
    # Create test files
    file1 = Path(temp_dir) / "agent_memory.md"
    file1.write_text("# Agent Memory\nAI agents need persistent memory.\nMemory helps maintain context.")
    
    file2 = Path(temp_dir) / "sqlite_guide.md"
    file2.write_text("# SQLite Guide\nSQLite is a lightweight database.\nFTS5 enables full-text search.")
    
    file3 = Path(temp_dir) / "python_tips.md"
    file3.write_text("# Python Tips\nPython is a versatile language.\nUse virtual environments.")
    
    yield temp_dir, file1, file2, file3
    shutil.rmtree(temp_dir)


class TestSearchPositive:
    """Positive test cases: search should work correctly."""
    
    def test_search_simple_query(self, temp_index_dir, temp_markdown_files):
        """Search for a simple term that exists in indexed files."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        # Add files to index
        add_file(file1, index_path, title="Agent Memory", summary="Memory patterns")
        add_file(file2, index_path, title="SQLite Guide", summary="Database guide")
        
        # Search for 'agent'
        results = search("agent", index_path)
        
        assert results is not None
        assert len(results) > 0
        assert results[0]['title'] == "Agent Memory"
    
    def test_search_returns_ranked_results(self, temp_index_dir, temp_markdown_files):
        """Search results should be ranked by relevance (BM25)."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Memory patterns for agents")
        add_file(file3, index_path, title="Python Tips", summary="Python techniques")
        
        # Search for 'agent' - should rank Agent Memory higher
        results = search("agent", index_path)
        
        assert len(results) > 0
        assert results[0]['title'] == "Agent Memory"
        assert 'relevance' in dict(results[0])
    
    def test_search_with_limit(self, temp_index_dir, temp_markdown_files):
        """Search with custom limit parameter."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        # Add multiple files
        add_file(file1, index_path, title="File 1", summary="Python memory")
        add_file(file2, index_path, title="File 2", summary="Python database")
        add_file(file3, index_path, title="File 3", summary="Python tips")
        
        # Search with limit of 1
        results = search("python", index_path, limit=1)
        
        assert len(results) == 1
    
    def test_search_within_specific_file(self, temp_index_dir, temp_markdown_files):
        """Search restricted to a specific file."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Memory systems")
        add_file(file2, index_path, title="SQLite Guide", summary="Database guide")
        
        # Search for 'database' in file2 only
        results = search("database", index_path, file_path=file2)
        
        assert results is not None
        assert len(results) == 1
        assert results[0]['path'] == str(file2.absolute())
    
    def test_search_includes_snippet(self, temp_index_dir, temp_markdown_files):
        """Search results should include snippets."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Memory patterns")
        
        results = search("agent", index_path)
        
        assert 'snippet' in dict(results[0])
        assert len(results[0]['snippet']) > 0
    
    def test_search_multiple_matching_files(self, temp_index_dir, temp_markdown_files):
        """Search that matches multiple files."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        # All files mention 'is' or similar terms
        add_file(file1, index_path, title="Agent Memory", summary="AI memory")
        add_file(file2, index_path, title="SQLite Guide", summary="Database guide")
        add_file(file3, index_path, title="Python Tips", summary="Python language")
        
        results = search("guide", index_path)
        
        assert len(results) >= 1
    
    def test_search_with_quoted_phrase(self, temp_index_dir, temp_markdown_files):
        """Search with quoted phrase for exact matching."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Persistent memory systems")
        
        results = search('"persistent memory"', index_path)
        
        assert results is not None
        assert len(results) > 0


class TestSearchNegative:
    """Negative test cases: search edge cases and error handling."""
    
    def test_search_empty_index(self, temp_index_dir):
        """Search on empty index should raise error."""
        index_path = Path(temp_index_dir)
        
        with pytest.raises(ValueError, match="Index is empty"):
            search("anything", index_path)
    
    def test_search_no_matching_results(self, temp_index_dir, temp_markdown_files):
        """Search for non-existent term should return empty."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Memory guide")
        
        results = search("nonexistentterm12345", index_path)
        
        assert results is None or len(results) == 0
    
    def test_search_invalid_fts_syntax(self, temp_index_dir, temp_markdown_files):
        """Invalid FTS5 syntax should return None (error caught)."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Memory patterns")
        
        # Invalid FTS5 syntax: unmatched quotes
        results = search('memory "unmatched quote', index_path)
        
        assert results is None
    
    def test_search_nonexistent_file_path(self, temp_index_dir, temp_markdown_files):
        """Search restricted to non-existent file should return empty."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Memory guide")
        
        nonexistent = Path(temp_dir) / "nonexistent.md"
        results = search("memory", index_path, file_path=nonexistent)
        
        assert results is None or len(results) == 0
    
    def test_search_limit_zero(self, temp_index_dir, temp_markdown_files):
        """Search with limit of 0 should return no results."""
        temp_dir, file1, file2, file3 = temp_markdown_files
        index_path = Path(temp_index_dir)
        
        add_file(file1, index_path, title="Agent Memory", summary="Memory guide")
        
        results = search("memory", index_path, limit=0)
        
        assert len(results) == 0
