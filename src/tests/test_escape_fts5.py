"""Tests for _escape_fts5 helper function."""


from mindex.cmd_search import _escape_fts5


class TestEscapeFts5Positive:
    """Positive test cases for _escape_fts5."""

    def test_simple_word(self):
        """Test escaping a simple word."""
        assert _escape_fts5("hello") == '"hello"'

    def test_multi_word(self):
        """Test escaping a multi-word query."""
        assert _escape_fts5("hello world") == '"hello world"'

    def test_already_quoted(self):
        """Test that already-quoted input is handled."""
        assert _escape_fts5('"test"') == '"""test"""'

    def test_uppercase(self):
        """Test preserving case."""
        assert _escape_fts5("Python") == '"Python"'

    def test_numbers(self):
        """Test query with numbers."""
        assert _escape_fts5("test123") == '"test123"'


class TestEscapeFts5Negative:
    """Negative/edge case test cases for _escape_fts5."""

    def test_embedded_double_quotes(self):
        """Test that embedded double quotes are doubled."""
        result = _escape_fts5('say "hello"')
        assert result == '"say ""hello"""'

    def test_multiple_embedded_quotes(self):
        """Test multiple embedded double quotes."""
        result = _escape_fts5('"a" and "b"')
        assert result == '"""a"" and ""b"""'

    def test_only_quotes(self):
        """Test query that is only quotes."""
        result = _escape_fts5('""')
        assert result == '""""""'

    def test_empty_string(self):
        """Test empty string input."""
        assert _escape_fts5("") == '""'

    def test_whitespace_only(self):
        """Test whitespace-only query."""
        assert _escape_fts5("   ") == '"   "'

    def test_special_fts_chars(self):
        """Test that FTS special chars are wrapped in quotes."""
        result = _escape_fts5("+ - *")
        assert result == '"+ - *"'

    def test_unicode(self):
        """Test unicode characters are preserved."""
        assert _escape_fts5("café") == '"café"'

    def test_mixed_quotes_and_unicode(self):
        """Test mixed quotes and unicode."""
        result = _escape_fts5('café "test"')
        assert result == '"café ""test"""'
