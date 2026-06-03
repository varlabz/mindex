import tempfile
from pathlib import Path

from mindex.mindex import MARK_START, MARK_END, PAD, _extract_snippets, add_file, search_file


def test_search_file_single_match():
    """Test search_file returns a single highlighted match."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("The quick brown fox jumps over the lazy dog.")
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "fox")

        assert len(results) == 1
        assert "fox" in results[0].snippet
        assert results[0].position == 16  # "The quick brown fox" -> fox starts at index 16


def test_search_file_multiple_matches():
    """Test search_file returns multiple highlighted matches."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("apple banana apple cherry apple")
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "apple")

        assert len(results) == 3
        for r in results:
            assert "apple" in r.snippet


def test_search_file_no_matches():
    """Test search_file returns empty list when no matches."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("hello world")
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "nonexistent")

        assert results == []


def test_search_file_with_limit():
    """Test search_file respects the limit parameter."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("cat cat cat cat cat")
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "cat", limit=2)

        assert len(results) == 2


def test_search_file_multi_word_query():
    """Test search_file with multi-word FTS query."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("the quick brown fox jumps over the lazy dog")
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "quick brown")

        assert len(results) >= 1
        assert "quick brown" in results[0].snippet


def test_search_file_snippet_contains_context():
    """Test that returned snippets include surrounding context."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("prefix text before the keyword suffix text after")
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "keyword")

        assert len(results) == 1
        assert "before" in results[0].snippet
        assert "suffix" in results[0].snippet


def test_search_file_unindexed_file():
    """Test search_file returns empty list for a file not in the index."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("hello world")
        # Do NOT add the file to the index

        results = search_file(index_dir, test_file, "hello")

        assert results == []


def test_search_file_limit():
    """Test search_file respects the limit parameter."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("test test test test test")
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "test", limit=2)

        assert len(results) == 2


def test_search_file_position_accuracy():
    """Test that position reflects real byte offset in original content."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        content = "aaa bbb aaa ccc aaa"
        test_file.write_text(content)
        add_file(index_dir, test_file)

        results = search_file(index_dir, test_file, "aaa")

        assert len(results) == 3
        # Verify positions match actual occurrences in original content
        for i, r in enumerate(results):
            assert content[r.position : r.position + 3] == "aaa"


def test_search_file_file_not_indexed():
    """Test search_file returns empty for file not in index."""
    with tempfile.TemporaryDirectory() as tmp:
        index_dir = Path(tmp) / "index"
        index_dir.mkdir()
        test_file = Path(tmp) / "test.md"
        test_file.write_text("some content")

        results = search_file(index_dir, test_file, "content")

        assert results == []


# ============================================================
# _extract_snippets tests
# ============================================================


class TestExtractSnippetsPositive:
    """Positive test cases for _extract_snippets."""

    def test_single_match(self):
        """Test extraction of a single highlighted match."""
        highlighted = f"prefix {MARK_START}keyword{MARK_END} suffix"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1
        assert MARK_START not in results[0].snippet
        assert MARK_END not in results[0].snippet
        assert "prefix" in results[0].snippet
        assert "suffix" in results[0].snippet

    def test_multiple_matches(self):
        """Test extraction of multiple highlighted matches."""
        highlighted = f"{MARK_START}first{MARK_END} middle {MARK_START}second{MARK_END} end"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 2
        assert "first" in results[0].snippet
        assert "second" in results[1].snippet

    def test_respects_limit(self):
        """Test that limit parameter caps the number of results."""
        highlighted = (
            f"{MARK_START}a{MARK_END} "
            f"{MARK_START}b{MARK_END} "
            f"{MARK_START}c{MARK_END} "
            f"{MARK_START}d{MARK_END}"
        )
        results = _extract_snippets(highlighted, limit=2)

        assert len(results) == 2

    def test_position_calculation(self):
        """Test that positions are computed correctly accounting for marker overhead."""
        highlighted = f"{MARK_START}term1{MARK_END} {MARK_START}term2{MARK_END}"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 2
        # First match: position should be 0 (no overhead before it)
        assert results[0].position == 0
        # Second match: pos=22 (8+5+8+1), real_pos = 22 - 1*16 = 6
        assert results[1].position == 6

    def test_snippet_includes_context_before(self):
        """Test that snippets include context before the match."""
        long_prefix = "x" * 100
        highlighted = f"{long_prefix}{MARK_START}keyword{MARK_END}"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1
        # Should include some of the prefix (up to PAD chars)
        assert "keyword" in results[0].snippet

    def test_snippet_includes_context_after(self):
        """Test that snippets include context after the match."""
        highlighted = f"{MARK_START}keyword{MARK_END}{PAD * 'y'}"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1
        # Should include some of the suffix
        assert "keyword" in results[0].snippet
        assert "y" in results[0].snippet

    def test_empty_highlighted(self):
        """Test with empty string."""
        results = _extract_snippets("", limit=5)
        assert results == []

    def test_no_markers(self):
        """Test with text that has no markers."""
        results = _extract_snippets("just plain text without any markers", limit=5)
        assert results == []

    def test_only_open_marker(self):
        """Test with only an open marker and no closing marker."""
        highlighted = f"text {MARK_START} incomplete"
        results = _extract_snippets(highlighted, limit=5)
        assert results == []

    def test_only_close_marker(self):
        """Test with only a close marker and no open marker."""
        highlighted = f"text {MARK_END} incomplete"
        results = _extract_snippets(highlighted, limit=5)
        assert results == []

    def test_limit_zero(self):
        """Test that limit=0 returns empty list."""
        highlighted = f"{MARK_START}keyword{MARK_END}"
        results = _extract_snippets(highlighted, limit=0)
        assert results == []

    def test_limit_one(self):
        """Test that limit=1 returns exactly one result."""
        highlighted = f"{MARK_START}a{MARK_END} {MARK_START}b{MARK_END}"
        results = _extract_snippets(highlighted, limit=1)
        assert len(results) == 1

    def test_adjacent_matches(self):
        """Test matches that are directly adjacent with no space."""
        highlighted = f"{MARK_START}a{MARK_END}{MARK_START}b{MARK_END}"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 2
        assert "a" in results[0].snippet
        assert "b" in results[1].snippet

    def test_overlapping_markers_ignored(self):
        """Test that nested/overlapping markers are handled gracefully."""
        # Open marker inside another match should be found as next match start
        highlighted = f"{MARK_START}first{MARK_END}{MARK_START}second{MARK_END}"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 2

    def test_omark_at_position_zero(self):
        """Test that MARK_START at position 0 is handled correctly."""
        highlighted = f"{MARK_START}keyword{MARK_END} rest of text"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1
        assert results[0].position == 0
        assert "keyword" in results[0].snippet
        assert "rest of text" in results[0].snippet

    def test_snippet_truncated_at_start(self):
        """Test that snippet doesn't go before index 0."""
        highlighted = f"{MARK_START}near start{MARK_END} rest of text"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1
        # Snippet should start at the beginning (no leading context possible)
        assert not results[0].snippet.startswith(" ")
        assert "near start" in results[0].snippet
        assert "rest of text" in results[0].snippet

    def test_snippet_truncated_at_end(self):
        """Test that snippet doesn't go past end of string."""
        highlighted = f"prefix {MARK_START}near end{MARK_END}"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1
        # Snippet should not contain markers (they are stripped)
        assert MARK_END not in results[0].snippet
        assert "near end" in results[0].snippet

    def test_large_limit_exceeds_matches(self):
        """Test that large limit doesn't cause errors when fewer matches exist."""
        highlighted = f"{MARK_START}one{MARK_END}"
        results = _extract_snippets(highlighted, limit=1000)

        assert len(results) == 1

    def test_whitespace_around_markers(self):
        """Test markers with various whitespace patterns."""
        highlighted = f"  {MARK_START}keyword{MARK_END}  "
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1
        assert "keyword" in results[0].snippet

    def test_empty_marker_content(self):
        """Test markers with empty content between them."""
        highlighted = f"text {MARK_START}{MARK_END} more text"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 1

    def test_unicode_in_snippet(self):
        """Test that unicode characters are preserved in snippets."""
        highlighted = f"{MARK_START}日本語{MARK_END} {MARK_START}émoji{MARK_END}"
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 2
        assert "日本語" in results[0].snippet
        assert "émoji" in results[1].snippet

    def test_many_matches_with_limit(self):
        """Test extracting from many matches with a small limit."""
        terms = " ".join(f"{MARK_START}term{i}{MARK_END}" for i in range(20))
        results = _extract_snippets(terms, limit=3)

        assert len(results) == 3
        assert "term0" in results[0].snippet
        assert "term1" in results[1].snippet
        assert "term2" in results[2].snippet

    def test_position_with_many_matches(self):
        """Test position calculation across multiple matches."""
        terms = [f"{MARK_START}t{i}{MARK_END}" for i in range(5)]
        highlighted = " ".join(terms)
        results = _extract_snippets(highlighted, limit=5)

        assert len(results) == 5
        # Each position = pos_in_highlighted - cumulative_marker_overhead
        # Match 0: pos=0, real_pos=0
        # Match 1: pos=19, real_pos=19-16=3
        # Match 2: pos=38, real_pos=38-32=6
        # Match 3: pos=57, real_pos=57-48=9
        # Match 4: pos=76, real_pos=76-64=12
        expected_positions = [0, 3, 6, 9, 12]
        for i, r in enumerate(results):
            assert r.position == expected_positions[i]
