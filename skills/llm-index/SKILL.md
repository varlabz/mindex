---
name: llm-index
description: "Search indexed files and extract information using mindex: search, fsearch, read, and add files to index."
argument-hint: "request"
allowed-tools: shell
compatibility: Requires uv (uvx).
metadata:
  tools: "uv (uvx), mindex"
  index: "SQLite FTS5"
---

# LLM Index

<index_dir> is mandatory for all commands and specifies the directory containing the mindex database.
If not provided, show error and terminate execution.

All commands use `uvx` to run `mindex` from the remote Git repo — no permanent installation needed.

**Base command**

```bash
uvx --from git+https://github.com/varlabz/mindex mindex --index-dir <index_dir> <subcommand> [options]
```

---

## Add Files to Index

Add one or more files to the searchable index. Supports glob patterns to batch-index multiple files at once. Files are stored with their full absolute path, content, size, and a SHA-256 hash. Re-adding an existing file updates its content and timestamp.

```bash
mindex --index-dir <index_dir> add <file_or_glob>
```

### Examples

```bash
# Add a single file
mindex --index-dir <index_dir> add notes/sqlite.md

# Add all markdown files in a directory
mindex --index-dir <index_dir> add 'docs/**/*.md'

# Add file with tilde expansion
mindex --index-dir <index_dir> add ~/projects/readme.md
```

---

## Search

Full-text search across all indexed files using FTS5.
Use FTS5 query syntax for advanced search capabilities (e.g., exact phrases with quotes, boolean operators).
**Minimum query length: 3 characters.** Shorter queries will be rejected.
Optionally filter results by file path using a glob pattern.

```bash
mindex --index-dir <index_dir> search "<query>" [path_glob] [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--limit` | `-n` | 10 | Maximum number of results |
| `--format` | `-f` | `json` | Output format: `json` or `text` |

### Examples

```bash
# Search all indexed files
mindex --index-dir <index_dir> search "sqlite fts5"

# Search with result limit
mindex --index-dir <index_dir> search "agent memory" --limit 20

# Search filtered by file path (glob)
mindex --index-dir <index_dir> search "memory" "notes/*.md"

# Plain text output
mindex --index-dir <index_dir> search "transformer architecture" --format text

# Exact phrase search with quotes
mindex --index-dir <index_dir> search '"exact phrase match"'
```

---

## Search Inside a File (fsearch)

Search within a specific indexed file using FTS5.
Returns multiple matching snippets with character positions and context (~40 characters on each side).
Useful for focused searches when you know which file contains the information you need.

```bash
mindex --index-dir <index_dir> fsearch "<query>" <file_path> [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--limit` | `-n` | 10 | Maximum number of snippets |
| `--format` | `-f` | `json` | Output format: `json` or `text` |

### Examples

```bash
# Search within a specific file
mindex --index-dir <index_dir> fsearch "fts5 tokenizer" notes/sqlite.md

# Search with result limit
mindex --index-dir <index_dir> fsearch "fts5" notes/sqlite.md --limit 5

# Plain text output
mindex --index-dir <index_dir> fsearch "fts5" notes/sqlite.md --format text

# Search with tilde expansion and limit with text output
mindex --index-dir <index_dir> fsearch "fts5" ~/notes/sqlite.md --format text --limit 10
```

---

## Read File Content

Read the content of an indexed file, optionally from a specific position.
Can be used to read large files in chunks by specifying `--position` and `--size` to avoid loading the entire file at once.
Reads from the index database — the file must be indexed first with `add`.

```bash
mindex --index-dir <index_dir> read <file_path> [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--position` | `-p` | `0` | Start position (character offset) |
| `--size` | `-s` | `4000` | Number of characters to read |

### Examples

```bash
# Read first 4000 characters (default)
mindex --index-dir <index_dir> read notes/sqlite.md

# Read first 500 characters
mindex --index-dir <index_dir> read notes/sqlite.md --size 500

# Read content starting at character 1000, 2000 chars
mindex --index-dir <index_dir> read notes/sqlite.md --position 1000 --size 2000

# Read next chunk (continuation)
mindex --index-dir <index_dir> read notes/sqlite.md --position 2000 --size 2000
```

---

## Info

Show metadata about indexed files — path, size, last updated timestamp.
Useful for checking whether a file is indexed, listing files matching a glob pattern, or reviewing file properties without reading the full content.

```bash
mindex --index-dir <index_dir> info <file_or_glob> [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--format` | `-f` | `json` | Output format: `json` or `text` |

### Examples

```bash
# Show info for a specific file
mindex --index-dir <index_dir> info notes/sqlite.md

# List info for files matching a glob pattern
mindex --index-dir <index_dir> info 'notes/*.md'

# Plain text output
mindex --index-dir <index_dir> info notes/sqlite.md --format text
```

---

## Lint Index

Check the integrity of the index — verifies all indexed files still exist on disk and optionally belong to a specific directory.

```bash
mindex --index-dir <index_dir> lint [directory] [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--format` | `-f` | `json` | Output format: `json` or `text` |
| `--fix` | — | `false` | Delete records for files that no longer exist |

### Examples

```bash
# Lint all indexed files
mindex --index-dir <index_dir> lint

# Lint files in a specific directory
mindex --index-dir <index_dir> lint notes/
```

---

## Remove File from Index (dangerous)

Remove one or more files from the index (does **not** delete the actual file on disk).
Supports glob patterns to batch-remove multiple files at once.
It's **dangerous** to use this command, as it permanently removes entries from the index.

```bash
mindex --index-dir <index_dir> rm <file_or_glob>
```

### Examples

```bash
# Remove single file from index
mindex --index-dir <index_dir> rm notes/old-notes.md

# Batch-remove all files matching a pattern
mindex --index-dir <index_dir> rm 'temp/*.md'
```

---

## Tips

| Scenario | Recommendation |
|----------|---------------|
| **Search then read** | Use `search` to find relevant files, then `read` to get full content |
| **Focused search** | Use `fsearch` when you know which file contains the answer — faster and more precise |
| **Large files** | Use `read` with `--position` and `--size` to read in chunks |
| **Batch indexing** | Use `add` with glob patterns (e.g., `'docs/**/*.md'`) to index many files at once |
| **Filter by path** | Use the optional `path` argument in `search` to narrow results to specific directories |
| **Re-index changed files** | Use `add` again on the same file — it updates content and timestamp automatically |
