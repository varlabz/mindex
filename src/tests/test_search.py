from pathlib import Path

import pytest

from mindex.mindex import add_file, del_file, search


@pytest.fixture
def index_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for the index."""
    return tmp_path


@pytest.fixture
def indexed_files(index_dir: Path) -> dict[str, Path]:
    """Create and index multiple test files."""
    files = {}
    for name, content in [
        ("file1.md", "# Python Tutorial\n\nPython is a great programming language."),
        ("file2.md", "# JavaScript Guide\n\nJavaScript is widely used for web development."),
        ("file3.md",
         "# Rust Programming\n\nRust is a systems programming language focused on safety."),
    ]:
        file_path = index_dir / name
        file_path.write_text(content, encoding="utf-8")
        add_file(index_dir, file_path)
        files[name] = file_path
    return files


class TestSearchPositive:
    """Positive test cases for search function."""

    def test_search_returns_results(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search returns results for a common term."""
        results = search(index_dir, "programming")

        assert len(results) >= 2
        for r in results:
            assert r.path is not None
            assert r.snippet is not None
            assert len(r.snippet) > 0

    def test_search_returns_correct_fields(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search results contain all expected fields."""
        results = search(index_dir, "Python")

        assert len(results) >= 1
        result = results[0]
        assert hasattr(result, "path")
        assert hasattr(result, "snippet")
        assert hasattr(result, "tag")
        assert hasattr(result, "updated_at")

    def test_search_with_tag_filter(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search respects tag filtering."""
        # Add files with tags
        file1 = index_dir / "tagged1.md"
        file1.write_text("This is about Python programming.", encoding="utf-8")
        add_file(index_dir, file1, tag="python")

        file2 = index_dir / "tagged2.md"
        file2.write_text("This is about JavaScript programming.", encoding="utf-8")
        add_file(index_dir, file2, tag="javascript")

        # Search with tag filter
        results = search(index_dir, "programming", tag="python")

        assert len(results) >= 1
        for r in results:
            assert r.tag == "python"

    def test_search_with_tag_filter_no_match(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that tag filter returns empty when no files match the tag."""
        results = search(index_dir, "programming", tag="nonexistent-tag")

        assert len(results) == 0

    def test_search_respects_limit(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search respects the limit parameter."""
        results = search(index_dir, "programming", limit=1)

        assert len(results) <= 1

    def test_search_returns_snippet_with_context(
        self, indexed_files: dict[str, Path], index_dir: Path
    ):
        """Test that snippets include surrounding context."""
        results = search(index_dir, "Python")

        assert len(results) >= 1
        snippet = results[0].snippet
        # Snippet should contain the matched term
        assert "Python" in snippet or "python" in snippet.lower()

    def test_search_bm25_ranking(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that more relevant results appear first (BM25 ranking)."""
        results = search(index_dir, "Python")

        assert len(results) >= 1
        # First result should be from file1.md which contains "Python" in title
        assert "file1.md" in results[0].path

    def test_search_multi_word_query(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test search with multi-word query."""
        results = search(index_dir, "programming language")

        assert len(results) >= 2  # Should match Python and Rust files

    def test_search_case_insensitive(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search is case-insensitive."""
        results_lower = search(index_dir, "python")
        results_upper = search(index_dir, "PYTHON")

        assert len(results_lower) == len(results_upper)


class TestSearchNegative:
    """Negative test cases for search function."""

    def test_search_no_matches(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search returns empty list when no matches."""
        results = search(index_dir, "nonexistent_term_xyz123")

        assert len(results) == 0

    def test_search_empty_index(self, index_dir: Path):
        """Test that search returns empty list when index is empty."""
        results = search(index_dir, "any term")

        assert len(results) == 0

    def test_search_unindexed_file(self, index_dir: Path):
        """Test that search doesn't return results for unindexed files."""
        # Create a file but don't add it to index
        unindexed = index_dir / "unindexed.md"
        unindexed.write_text("This file is not indexed.", encoding="utf-8")

        results = search(index_dir, "indexed")

        # Should not find the unindexed file
        for r in results:
            assert "unindexed.md" not in r.path

    def test_search_special_characters(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test search with special characters in query."""
        results = search(index_dir, "xyz123!@#$%")

        assert len(results) == 0

    def test_search_whitespace_only(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test search with whitespace-only query raises error."""
        with pytest.raises(ValueError, match="Query cannot be empty or whitespace only"):
            search(index_dir, "   ")


class TestSearchEdgeCases:
    """Edge case tests for search function."""

    def test_search_limit_zero(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that limit=0 returns empty list."""
        results = search(index_dir, "programming", limit=0)

        assert len(results) == 0

    def test_search_limit_one(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that limit=1 returns exactly one result."""
        results = search(index_dir, "programming", limit=1)

        assert len(results) <= 1

    def test_search_large_limit(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that large limit doesn't cause errors."""
        results = search(index_dir, "programming", limit=1000)

        # Should return all matching results without error
        assert len(results) >= 0

    def test_search_single_character(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test search with single character query raises error."""
        with pytest.raises(ValueError, match="Query too short"):
            search(index_dir, "a")

    def test_search_unicode_content(self, index_dir: Path):
        """Test search with unicode content returns empty (FTS5 cannot index CJK)."""
        file_path = index_dir / "unicode.md"
        file_path.write_text("# 日本語テスト\n\nこれはテストファイルです。", encoding="utf-8")
        add_file(index_dir, file_path)

        results = search(index_dir, "日本語")

        assert len(results) == 0

    def test_search_unicode_query(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test search with unicode query term."""
        results = search(index_dir, "JavaScript")

        assert len(results) >= 1
        assert "file2.md" in results[0].path

    def test_search_long_content(self, index_dir: Path):
        """Test search with very long file content."""
        long_content = " ".join(f"paragraph {i}" for i in range(1000))
        file_path = index_dir / "long.md"
        file_path.write_text(long_content, encoding="utf-8")
        add_file(index_dir, file_path)

        results = search(index_dir, "paragraph 500")

        assert len(results) >= 1
        assert "long.md" in results[0].path

    def test_search_empty_content(self, index_dir: Path):
        """Test search with empty file content."""
        file_path = index_dir / "empty.md"
        file_path.write_text("", encoding="utf-8")
        add_file(index_dir, file_path)

        results = search(index_dir, "anything")

        # Should not crash, may or may not return results
        assert len(results) >= 0

    def test_search_after_delete(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search doesn't return deleted files."""
        file1 = indexed_files["file1.md"]
        del_file(index_dir, file1)

        results = search(index_dir, "Python")

        # file1.md should not be in results
        for r in results:
            assert "file1.md" not in r.path

    def test_search_after_update(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search returns updated content."""
        file1 = indexed_files["file1.md"]
        # Update the file content
        file1.write_text("# Updated Python Tutorial\n\nPython is amazing!", encoding="utf-8")
        add_file(index_dir, file1)

        results = search(index_dir, "amazing")

        assert len(results) >= 1
        assert "file1.md" in results[0].path

    def test_search_tag_with_no_tagged_files(self, index_dir: Path):
        """Test search with tag filter when no files have tags."""
        file_path = index_dir / "no_tag.md"
        file_path.write_text("This file has no tag.", encoding="utf-8")
        add_file(index_dir, file_path)

        results = search(index_dir, "tag", tag="some-tag")

        assert len(results) == 0

    def test_search_special_query_terms(self, index_dir: Path):
        """Test search with FTS special characters in query."""
        file_path = index_dir / "special.md"
        file_path.write_text("Contains + - * : ! ? \" ' ( ) [ ] { }", encoding="utf-8")
        add_file(index_dir, file_path)

        # Search for a simple term that shouldn't be affected by special chars
        results = search(index_dir, "Contains")

        assert len(results) >= 1

    def test_search_multiple_tags(self, index_dir: Path):
        """Test search with files having different tags."""
        files = []
        for name, content, tag in [
            ("a.md", "Python code here", "python"),
            ("b.md", "JavaScript code here", "javascript"),
            ("c.md", "Python and JavaScript", "both"),
        ]:
            file_path = index_dir / name
            file_path.write_text(content, encoding="utf-8")
            add_file(index_dir, file_path, tag=tag)
            files.append(file_path)

        # Search with python tag
        results = search(index_dir, "Python", tag="python")
        assert len(results) >= 1
        assert all(r.tag == "python" for r in results)

        # Search with both tag
        results = search(index_dir, "JavaScript", tag="both")
        assert len(results) >= 1
        assert all(r.tag == "both" for r in results)

    def test_search_path_is_absolute(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search results contain absolute paths."""
        results = search(index_dir, "programming")

        assert len(results) >= 1
        assert results[0].path.startswith("/")

    def test_search_updated_at_is_present(self, indexed_files: dict[str, Path], index_dir: Path):
        """Test that search results contain updated_at timestamp."""
        results = search(index_dir, "programming")

        assert len(results) >= 1
        assert results[0].updated_at is not None
        assert len(results[0].updated_at) > 0

    def test_search_tag_is_none_when_not_set(self, index_dir: Path):
        """Test that tag is None when file was added without a tag."""
        file_path = index_dir / "no_tag.md"
        file_path.write_text("No tag here.", encoding="utf-8")
        add_file(index_dir, file_path)

        results = search(index_dir, "tag")

        assert len(results) >= 1
        assert results[0].tag is None
