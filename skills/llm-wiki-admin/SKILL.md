---
name: llm-wiki-admin
description: "Manage wiki index: add files, remove files, view metadata, and list tags. Administrative commands for mindex-cli."
argument-hint: "command [options]"
allowed-tools: shell
compatibility: Requires uv (uvx).
metadata:
  tools: "uv (uvx), mindex-cli"
  index: "SQLite FTS5"
---

# LLM Wiki Admin — Index Management

All commands use `uvx` to run `mindex-cli` on the fly — no permanent installation needed.

**Base command:**

```bash
uvx --from git+https://github.com/varlabz/mindex mindex-cli --index <index_dir> <subcommand> [options]
```

---

## Add Files to Index

Digest markdown files into the searchable index. Title and summary are required for indexing.
Summary should be a concise description of the file's content to improve search relevance. 
The flag `--source` is optional and can be a URL for where the content came from (defaults to file path if not provided).
The flag `--tags` is optional but recommended for better organization and discoverability.
Before creating tags, check existing tags with `mindex-cli tags` to maintain consistency.
Reuses existing tags and creates new ones as needed. 

```bash
mindex-cli --index <index_dir> add <file.md> --title "<title>" --summary "<summary>" --tags <tag1> <tag2> --source "<source_url>"
```

**Options:**

| Flag | Short | Required | Description |
|------|-------|----------|-------------|
| `--title` | `-T` | Yes | Title for the indexed file |
| `--summary` | `-S` | Yes | Summary/description text |
| `--tags` | `-t` | No | Tags (space or comma separated, e.g. `ai, sqlite`) |
| `--source` | `-s` | No | Source URL or reference (defaults to file path) |
| `--index` | `-i` | Yes | Index directory (default: current dir) |

### Examples

```bash
# Basic add with title and summary
mindex-cli --index <index_dir> add notes/sqlite.md --title "SQLite FTS5 Guide" --summary "Indexing and searching with SQLite FTS5"

# Add with tags
mindex-cli --index <index_dir> add notes/sqlite.md --title "SQLite FTS5 Guide" --summary "Indexing guide" --tags ai sqlite database

# Add with source URL
mindex-cli --index <index_dir> add notes/api.md --title "API Reference" --summary "REST API docs" --source "https://example.com/api"
```

---

## File Info

Display metadata about an indexed file (title, summary, tags, source, etc.).

```bash
mindex-cli --index <index_dir> info <file.md>
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--text` | — | — | Output as plain text instead of JSON |
| `--index` | `-i` | current dir | Index directory |

### Examples

```bash
# Show file info (JSON)
mindex-cli --index <index_dir> info notes/sqlite.md

# Show file info (plain text)
mindex-cli --index <index_dir> info notes/sqlite.md --text
```

---

## Remove File from Index

Remove a file from the index (does not delete the actual file).

```bash
mindex-cli --index <index_dir> rm <file.md>
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--index` | `-i` | current dir | Index directory |

### Examples

```bash
# Remove file from index
mindex-cli --index <index_dir> rm notes/old-notes.md
```

---

## List Tags

List all tags across the indexed files.

```bash
mindex-cli --index <index_dir> tags
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--index` | `-i` | current dir | Index directory |

### Examples

```bash
# List all tags
mindex-cli --index <index_dir> tags
```

---

## Tips

| Scenario | Recommendation |
|----------|---------------|
| **Multiple indexes** | Use `--index` to maintain separate wikis (e.g., one per project) |
| **Missing title/summary** | `add` requires both `--title` and `--summary`. Provide meaningful values for better search results |
| **Tags** | Use consistent tag names for easier filtering and discovery |
