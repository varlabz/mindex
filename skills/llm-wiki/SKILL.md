---
name: llm-wiki-admin
description: "Manage wiki index: ingest files, remove files."
argument-hint: "request"
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
uvx --from git+https://github.com/varlabz/mindex mindex-cli --index-dir <index_dir> <subcommand> [options]
```

<index_dir> is mandatory for all commands and specifies the directory where the wiki index is stored. 
If not provided, show error and terminate execution.

---
## Initialization 
Create a `SCHEMA.md` template file to define the structure and rules for the wiki index in <index_dir> if it does not exist.
```markdown
# Wiki directory structure
summary/    # contains summary files with metadata and references to original files
raw/        # contains original files with raw content
index.md    # main index file listing all summaries with links
log.md      # log of all actions performed on the wiki index
SCHEMA.md   # defines the structure and rules for the wiki index

# Rules
- All summary files must be stored in the `summary/` directory.
  - must contain a title, reference to the original file, and relevant tags
  - reference to original file in the summary file in markdown format for better discoverability (e.g., `[Original](../raw/sqlite.md)`).
- The `index.md` file must list all summaries with links to their respective summary files for easy navigation.
- The `log.md` file must record all actions performed on the wiki for audit purposes.
  - All actions must be logged in the format: `## [YYYY-MM-DD] <action> | <file_path> or <one_line_short_description>`.
```

Always ensure `SCHEMA.md` exists in <index_dir> before performing any operations. If it does not exist, create it with the above content.
Always follow the structure defined in `SCHEMA.md` when adding files to the index.
---

## Ingest File

To ingest file make steps:
- Add a file in the searchable index.
- Create a summary file with title and store in `summary/` directory in <index_dir>.
- The file name for the summary is the same as the original file but prefixed with `summary/` (e.g., `raw/sqlite.md` → `summary/sqlite.md`).
- Add tags to summary file for better organization (e.g., `#database #sqlite`).
- Add reference to summary in `index.md` in <index_dir> with the title of the summary file for better discoverability (e.g., `- [SQLite Notes](summary/sqlite.md)`).

```bash
mindex-cli --index-dir <index_dir> add <file.md> -t raw
mindex-cli --index-dir <index_dir> add <summary_file.md> -t summary
```

### Examples

```bash
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

## Remove File from Index

Remove a file from the index (does not delete the actual file).

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
| **Tags** | Use consistent tag names for easier filtering and discovery |
