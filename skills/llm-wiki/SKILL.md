---
name: llm-wiki
description: "Search and read wiki files indexed with mindex-cli. Full-text search across indexed markdown content and retrieve file contents."
argument-hint: "<query>"
allowed-tools: shell
compatibility: Requires uv (uvx).
metadata:
  tools: "uv (uvx), mindex-cli"
  index: "SQLite FTS5"
---

# LLM Wiki — Search & Read

All commands use `uvx` to run `mindex-cli` on the fly — no permanent installation needed.

**Base command:**

```bash
uvx --from git+https://github.com/varlabz/mindex mindex-cli --index <index_dir> <subcommand> [options]
```

---

## Search 

Full-text search across all indexed markdown files or in a specific file using FTS5.
Use FTS5 query syntax for advanced search capabilities (e.g., exact phrases with quotes, boolean operators).
You can use search results for next steps, e.g. to read a specific file by passing the file name to the `mindex-cli read` command.
Change search request if don't get relevant results — try different keywords, use quotes for exact phrases, or check the indexed content for better search terms.
Filter results by tags using `--tags` to find files with specific tags. Can use multiple tags to narrow down results.
Can find avaliable tags with `mindex-cli tags` command.
Use `--file` to restrict search to a specific file, which is useful for large files or when you know the relevant file.
Don't combine `--file` and `--tags` in the same search command, as they serve different purposes — `--file` restricts to a single file, while `--tags` filters across all indexed files based on tags.

```bash
mindex-cli --index <index_dir> search "<query>"
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--limit` | `-l` | — | Maximum number of results |
| `--file` | `--path` | — | Restrict search to a specific file |
| `--tags` | `-t` | — | Filter by tags (space or comma separated) |
| `--text` | — | — | Output as plain text instead of JSON |
| `--index` | `-i` | current dir | Index directory |

### Examples

```bash
# Basic search
mindex-cli --index <index_dir> search "sqlite fts5"

# Search with result limit
mindex-cli --index <index_dir> search "agent memory" --limit 20

# Search within a specific file
mindex-cli --index <index_dir> search "agent memory" --file notes/agents.md

# Filter by tags
mindex-cli --index <index_dir> search "memory" --tags ai agents

# Plain text output
mindex-cli --index <index_dir> search "transformer architecture" --text
```

---

## Read File Content

Read the content of an indexed file, optionally from a specific position.
Can be used to read large files in chunks by specifying `--position` and `--size` to avoid loading the entire file into memory at once.

```bash
mindex-cli --index <index_dir> read <file.md>
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--position` | `-p` | `0` | Start position (character offset) |
| `--size` | `-s` | — | Number of characters to show |
| `--index` | `-i` | current dir | Index directory |

### Examples

```bash
# Read entire file content
mindex-cli --index <index_dir> read notes/sqlite.md

# Read first 500 characters
mindex-cli --index <index_dir> read notes/sqlite.md --size 500

# Read content starting at character 1000, 2000 chars
mindex-cli --index <index_dir> read notes/sqlite.md --position 1000 --size 2000
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
| **Large files** | Use `--position` and `--size` with `read` to read in chunks instead of loading the entire file |
| **FTS5 search syntax** | The search supports FTS5 query syntax — use quotes for exact phrases, e.g., `"exact phrase"` |
| **File not indexed** | `read` only works on files that have been added to the index first |
