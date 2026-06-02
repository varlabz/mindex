# mindex — Markdown Index

Lightweight markdown indexing and full-text search powered by SQLite FTS5.

**Features:**
- Index markdown files with metadata (titles, summaries, tags)
- Full-text search with BM25 relevance ranking
- Tag-based organization and filtering
- Hash-based change detection for incremental updates
- Zero dependencies beyond Python's standard library
- Single SQLite database file

## Installation

### Run without installation
```bash
uvx --from git+https://github.com/varlabz/mindex mindex-cli
```

## Quick Start

### 1. Index a markdown file

```bash
mindex-cli add articles/sqlite.md \
  --title "SQLite FTS5 Guide" \
  --summary "Complete guide to SQLite's full-text search"
```

### 2. Search the index

```bash
mindex-cli search "full-text search"
```

### 3. Tag files

```bash
mindex-cli add articles/sqlite.md --title "SQLite FTS5 Guide" --summary "Guide" --tags sqlite database search
```

### 4. List all tags

```bash
mindex-cli tags
```

### 5. Show file details

```bash
mindex-cli info articles/sqlite.md
```

## Usage

### Commands

#### `add` - Index or update a markdown file

```bash
mindex-cli add <file.md> --title "Title" --summary "Summary" [--tags tag1 tag2] [--source URL]
```

**Options:**
- `--title, -T`: Document title (required)
- `--summary, -S`: Brief description (required)
- `--tags, -t`: Space or comma-separated tags (optional)
- `--source, -s`: Source URL (optional, defaults to file path)

#### `search` - Search indexed content

```bash
mindex-cli search "query" [--limit 10] [--file path/to/file.md] [--json]
```

**Options:**
- `--limit, -l`: Maximum number of results (default: 10)
- `--file`: Search within a specific file only
- `--json`: Output as JSON instead of plain text

#### `tags` - List all tags

```bash
mindex-cli tags
```

#### `show` - Display file content

```bash
mindex-cli show <file.md> [--position 0] [--size 1000]
```

**Options:**
- `--position, -p`: Start position in characters (default: 0)
- `--size, -s`: Number of characters to show

#### `info` - Display file metadata

```bash
mindex-cli info <file.md> [--json]
```

**Options:**
- `--json`: Output as JSON instead of plain text

#### `rm` / `delete` - Remove file from index

```bash
mindex-cli rm <file.md>
mindex-cli delete <file.md>
```

### Global Options

```bash
mindex-cli --index ~/my-wiki <command>
```

Defaults to current directory. Use `--index` (or `-i`) to specify a custom index location.

## How It Works

### Database Schema

**docs** - Document metadata:
- `id`: Row identifier (primary key)
- `path`: Unique file path
- `source`: Source URL or reference (defaults to path)
- `title`: Document title
- `content`: Full markdown content
- `summary`: Brief description
- `word_count`: Word count
- `hash`: SHA-256 content hash for change detection
- `created_at`, `updated_at`: Timestamps

**docs_fts** - FTS5 virtual table:
- Full-text search index covering `title`, `content`, and `summary`
- BM25 relevance ranking
- Linked to `docs` table via `content_rowid`

**tags** - Tag associations:
- `doc_id`: Foreign key to docs.id
- `tag`: Tag name
- Many-to-many relationship between documents and tags
- Primary key on (doc_id, tag)

### Change Detection

Files are skipped during indexing when:
- File already exists in index
- SHA-256 hash matches (content unchanged)
- No new metadata provided

Enables fast incremental re-indexing.

## Testing

```bash
pytest tests/ -v
pytest tests/ --cov=mindex  # With coverage report
```

## Development

### Setup

```bash
git clone https://github.com/varlabz/mindex.git
cd mindex
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Linting

```bash
uv run black mindex/
uv run ruff check mindex/
uv run mypy mindex/
```

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new features
4. Submit a pull request

