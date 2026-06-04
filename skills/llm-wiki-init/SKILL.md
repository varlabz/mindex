---
name: llm-wiki-init
description: "Initialize wiki index directory with SCHEMA.md template."
argument-hint: "request"
allowed-tools: shell
---

# LLM Wiki Initialization

<index_dir> is mandatory for all commands and must specify the directory where the wiki index is stored. 
If not provided, show error and terminate execution.

Create a `SCHEMA.md` template file to define the structure and rules for the wiki index in <index_dir> if it does not exist.
```markdown
<index_dir> is mandatory for all commands and must specify the directory where the wiki index is stored. 
If not provided, show error and terminate execution.

# Wiki directory structure
summary/    # contains summary files with metadata and references to original files
raw/        # contains files with raw content
index.md    # main index file listing all summaries with links
log.md      # log of all actions performed on the wiki index
SCHEMA.md   # defines the structure and rules for the wiki index

# Rules
- Do not copy files to raw/.
- The index: `index.md` file must list all summaries with links to their respective summary files for easy navigation.
- The log: file`log.md` file must record all actions performed on the wiki for audit purposes.
  - All actions must be logged in the format: `## [YYYY-MM-DD] <action> | <file_path> or <one_line_short_description>`.
```


