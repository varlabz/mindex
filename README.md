# mindex — Markdown Index

A lightweight markdown indexing and full-text search system using SQLite FTS5.

**Features:**
- 📝 Index markdown files with metadata (title, summary, tags)
- 🔍 Full-text search with BM25 ranking
- 🏷️ Tag-based organization and filtering
- 🔄 Hash-based change detection (incremental updates)
- ⚡ Zero external dependencies (uses Python's built-in `sqlite3`)
- 📦 Single SQLite database for everything

## Installation

### From source
```bash
git clone https://github.com/yourusername/mindex.git
cd mindex
pip install -e .
```

### With development dependencies
```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Add markdown files to the index

```bash
mindex add articles/sqlite.md \
  --title "SQLite FTS5 Guide" \
  --summary "A comprehensive guide to SQLite's full-text search capabilities"
```

### 2. Search the index

```bash
mindex search "full-text search"
```

### 3. Add tags to files

```bash
mindex tags --add articles/sqlite.md sqlite,database,search
```

### 4. List all documents

```bash
mindex list
mindex list --tag sqlite
mindex list --tags  # Show tags for each document
```

### 5. View file details

```bash
mindex info articles/sqlite.md
```

## Usage

### Commands

#### `add` - Add or update a markdown file

```bash
mindex add <file.md> --title "Title" --summary "Summary" [--tags tag1 tag2] [--source URL]
```

**Options:**
- `--title, -T`: Document title (required)
- `--summary, -S`: Short summary (required)
- `--tags, -t`: Space or comma-separated tags (optional)
- `--source, -s`: Original source URL (optional, defaults to file path)

#### `search` - Full-text search

```bash
mindex search "query" [--limit 10] [--file path/to/file.md] [--json]
```

**Options:**
- `--limit, -l`: Maximum results (default: 10)
- `--file, -f`: Restrict search to a specific file
- `--json`: Output results as JSON (default: text)

#### `tags` - Manage tags

```bash
mindex tags --list                          # List all tags
mindex tags --add file.md "tag1,tag2"      # Add tags
mindex tags --remove file.md "tag1,tag2"   # Remove tags
```

#### `list` - List indexed documents

```bash
mindex list [--tag TAG] [--sort updated|title] [--tags]
```

**Options:**
- `--tag, -t`: Filter by tag
- `--sort, -s`: Sort by "updated" (default) or "title"
- `--tags`: Show tags for each document

#### `info` - Show file details

```bash
mindex info <file.md>
```

#### `rm` / `delete` - Remove file from index

```bash
mindex rm <file.md>
```

### Global Options

```bash
mindex --index_dir ~/my-wiki <command>
```

The default index directory is the current working directory. Use `--index_dir` to specify a custom location.

## Python API

```python
from pathlib import Path
from mindex import add_file, search, manage_tags

index_path = Path(".")

# Add a file
add_file(
    Path("articles/sqlite.md"),
    index_path=index_path,
    tags=["sqlite", "database"],
    title="SQLite Guide",
    summary="Learn SQLite FTS5"
)

# Search
results = search("full-text search", index_path=index_path, limit=10)
for row in results:
    print(f"{row['title']}: {row['snippet']}")

# Manage tags
manage_tags(
    Path("articles/sqlite.md"),
    index_path=index_path,
    add_tags=["important"]
)
```

## How It Works

### Database Schema

**docs** - Main document table:
- `path`: Unique file path
- `title`: Document title
- `content`: Full markdown content
- `summary`: Short description
- `word_count`: Number of words
- `hash`: SHA-256 hash for change detection
- `created_at`, `updated_at`: Timestamps

**docs_fts** - Virtual FTS5 table:
- Enables full-text search across `title`, `content`, and `summary`
- Uses BM25 ranking for relevance

**tags** - Tag association table:
- Links documents to tags
- Supports efficient tag-based filtering

### Change Detection

Files are skipped during indexing if:
- The file exists in the index
- The SHA-256 hash matches (no changes)
- No custom metadata is provided

This allows for fast incremental updates when re-running the indexer.

## Testing

Run the test suite:

```bash
pytest tests/ -v
pytest tests/ --cov=mindex  # With coverage
```

## Development

### Setup development environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

### Code quality

```bash
black mindex/
ruff check mindex/
mypy mindex/
```

## License

MIT License - see LICENSE file for details

## Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

## Author

Your Name - [@yourusername](https://twitter.com/yourusername)
