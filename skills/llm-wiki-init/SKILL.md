---
name: llm-wiki-init
description: "Initialize wiki index directory with SCHEMA.md template."
argument-hint: "request"
allowed-tools: shell
---

# LLM Wiki Initialization

<index_dir> is mandatory for all commands and specifies the directory where the wiki index is stored. 
If not provided, show error and terminate execution.

Create a `SCHEMA.md` template file to define the structure and rules for the wiki index in <index_dir> if it does not exist.
```markdown
# Wiki directory structure
summary/    # contains summary files with metadata and references to original files
raw/        # contains original files with raw content
index.md    # main index file listing all summaries with links
log.md      # log of all actions performed on the wiki index
SCHEMA.md   # defines the structure and rules for the wiki index

# Rules
- All summary files must be stored in the `summary/` in <index_dir> directory.
  - must contain a title, summary, reference to the original file, and relevant tags.
  - summary should be concise and informative, highlighting key points from the original file.
  - reference to the original file (e.g., `[Original](../raw/sqlite.md)`).
  - tags to summary file (e.g., `#database #sqlite`).
- The `index.md` file must list all summaries with links to their respective summary files for easy navigation.
- The `log.md` file must record all actions performed on the wiki for audit purposes.
  - All actions must be logged in the format: `## [YYYY-MM-DD] <action> | <file_path> or <one_line_short_description>`.
```


