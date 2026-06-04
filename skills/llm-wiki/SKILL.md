---
name: llm-wiki
description: "Manage wiki index: ingest files, remove files."
argument-hint: "request"
allowed-tools: shell
compatibility: Requires uv (uvx).
metadata:
  tools: "uv (uvx), mindex-cli"
  index: "SQLite FTS5"
---

# LLM Wiki 

<index_dir> is mandatory for all commands and specifies the directory where the wiki index is stored. 
If not provided, show error and terminate execution.

`SCHEMA.md` is required in <index_dir> before performing any operations. 
If it does not exist, show error and terminate execution.

Read the `SCHEMA.md` template file to understand the structure and rules for the wiki index in <index_dir> before using any commands.
Must follow precisely the instructions defined in `SCHEMA.md` in <index_dir>.

All commands use `uvx` to run `mindex-cli` on the fly — no permanent installation needed.

**Base command:**

```bash
uvx --from git+https://github.com/varlabz/mindex mindex-cli --index-dir <index_dir> <subcommand> [options]
```

---

## Ingest File

- Add a file in the searchable index.
- The file name for the summary is the same as the original file with replaced directory dividers on '-' (e.g., `raw/sqlite.md` → `summary/raw-sqlite.md`).
- A Summary file must be stored in the `summary/` in <index_dir> directory.
  - must contain a title, summary, reference to the original file, and relevant tags.
  - summary should be concise and informative, highlighting key points from the original file.
  - reference to the original file (e.g., `[Original](../raw/sqlite.md)`).
  - tags to summary file (e.g., `#database #sqlite`).
- Update index file.
- Update log file after execution.

```bash
mindex-cli --index-dir <index_dir> add <file.md> -t raw
mindex-cli --index-dir <index_dir> add <summary_file.md> -t summary
```

### Examples

```bash
# simple case
mindex-cli --index-dir <index_dir> add raw/sqlite.md -t raw
mindex-cli --index-dir <index_dir> add summary/raw-sqlite.md -t summary

# with long path
mindex-cli --index-dir <index_dir> add raw/notes/sqlite.md -t raw
mindex-cli --index-dir <index_dir> add summary/raw-notes-sqlite.md -t summary

# with absolute path
mindex-cli --index-dir <index_dir> add /home/user/wiki/raw/sqlite.md -t raw
mindex-cli --index-dir <index_dir> add summary/home-user-wiki-summary-sqlite.md -t summary
```
---

## Search (default command) 

Full-text search across all indexed markdown files using FTS5.
Use FTS5 query syntax for advanced search capabilities (e.g., exact phrases with quotes, boolean operators).
- Search in summaries (tag `summary`) for more concise results, then expand to raw files if needed.
- Search in raw files (tag `raw`) for more detailed information if summaries don't provide enough context.
- Search in file with `mindex-cli file` command for more focused search within a specific file.
- Read specific files with `mindex-cli read` command to get full content when you find relevant summaries or search results.
- Change search request if don't get relevant results — try different keywords, use quotes for exact phrases.
- Update log file after execution.

```bash
mindex-cli --index-dir <index_dir> search "<query>" [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--tag` | `-t` | — | Filter by a tag |
| `--limit` | `-n` | 10 | Maximum number of results |
| `--format` | `-f` | `json` | Output format: `json` or `text` |
| `--index-dir` | — | current dir | Index directory |

### Examples

```bash
# Search everywhere
mindex-cli --index-dir <index_dir> search "sqlite fts5"

# Search with result limit
mindex-cli --index-dir <index_dir> search "agent memory" --limit 20

# Search with tag `summary` for search in summaries
mindex-cli --index-dir <index_dir> search "memory" --tag summary

# Search with tag `raw` for search in original files
mindex-cli --index-dir <index_dir> search "memory" --tag raw

# Plain text output
mindex-cli --index-dir <index_dir> search "transformer architecture" --format text
```

---

## Search Inside a File

Search within a specific indexed file using FTS5.
Useful for focused searches when you know which file contains the information you need.
Update log file after execution.

```bash
mindex-cli --index-dir <index_dir> file <file.md> "<query>" [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--limit` | `-n` | 10 | Maximum number of results |
| `--format` | `-f` | `json` | Output format: `json` or `text` |
| `--index-dir` | `-i` | current dir | Index directory |

### Examples

```bash
# Search within a specific file
mindex-cli --index-dir <index_dir> file notes/sqlite.md "fts5 tokenizer"

# Search with result limit
mindex-cli --index-dir <index_dir> file notes/sqlite.md "fts5" --limit 5

# Plain text output
mindex-cli --index-dir <index_dir> file notes/sqlite.md "fts5" --format text
```

---

## Read File Content

Read the content of an indexed file, optionally from a specific position.
Can be used to read large files in chunks by specifying `--position` and `--size` to avoid loading the entire file into memory at once.
Update log file after execution.

```bash
mindex-cli --index-dir <index_dir> read <file.md> [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--position` | `-p` | `0` | Start position (character offset) |
| `--size` | `-s` | `4000` | Number of characters to show |
| `--index-dir` | `-i` | current dir | Index directory |

### Examples

```bash
# Read first 4000 characters (default)
mindex-cli --index-dir <index_dir> read notes/sqlite.md

# Read first 500 characters
mindex-cli --index-dir <index_dir> read notes/sqlite.md --size 500

# Read content starting at character 1000, 2000 chars
mindex-cli --index-dir <index_dir> read notes/sqlite.md --position 1000 --size 2000
```

---

## Info

Show metadata about an indexed file — path, size, last updated timestamp, and tag.
Useful for checking whether a file is indexed and reviewing its properties without reading the full content.
Update log file after execution.

```bash
mindex-cli --index-dir <index_dir> info <file.md> [options]
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--format` | `-f` | `json` | Output format: `json` or `text` |
| `--index-dir` | — | current dir | Index directory |

### Examples

```bash
# Show file info (JSON output)
mindex-cli --index-dir <index_dir> info raw/sqlite.md

# Show file info (text output)
mindex-cli --index-dir <index_dir> info raw/sqlite.md --format text
```

---

## Lint Index Directory

- Check the integrity of the wiki index directory, ensuring all required files are present and correctly formatted according to `SCHEMA.md`.
- Iterate through all directories defined in `SCHEMA.md` and call `./scripts/lint.sh` for each directory to validate the files within or fix.
- Do not fix automatically, only if requested via `fix` command.
- Update log file after execution.

```bash
# lint the directory structure/index
./scripts/lint.sh <index_dir> <directory> check

# fix the the directory structure/index
./scripts/lint.sh <index_dir> <directory> fix
```

---

## Remove File from Index (dangerous)

Remove a file from the index (does not delete the actual file).
Update log file after execution.

```bash
mindex-cli --index-dir <index_dir> rm <file.md>
```

**Options:**

| Flag | Short | Default | Description |
|------|-------|---------|-------------|
| `--index-dir` | — | current dir | Index directory |

### Examples

```bash
# Remove file from index
mindex-cli --index-dir <index_dir> rm notes/old-notes.md
```

---

## Tips

| Scenario | Recommendation |
|----------|---------------|
| **Multiple indexes** | Use `--index-dir` to maintain separate wikis (e.g., one per project) |
| **Search strategy** | Start with `--tag summary` for concise results, then expand to `--tag raw` or use `file` for deeper context |
| **Focused search** | Use `mindex-cli file` when you know which file contains the answer — faster and more precise than searching the whole index |
| **Large files** | Use `read` with `--position` and `--size` to read large files in chunks instead of loading the entire content |
