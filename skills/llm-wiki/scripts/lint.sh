#!/usr/bin/env bash
set -euo pipefail

# Usage: lint.sh <index-dir> <directory> [check|fix]
# Syncs mindex with actual files in the given directory (*.md).
# - Adds files in directory but missing from index
# - Removes index entries for files that no longer exist
#
# Arguments:
#   $1 - index directory path
#   $2 - directory to scan for .md files
#   $3 - mode: "check" (default) or "fix"

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <index-dir> <directory> [check|fix]" >&2
  exit 1
fi

INDEX_DIR="$1"
DIR="$2"
MODE="${3:-check}"
TAG="$DIR"

# Wrapper function for mindex-cli
mindex() {
  uvx --from git+https://github.com/varlabz/mindex mindex-cli --index-dir "$INDEX_DIR" "$@"
}

cd "$INDEX_DIR"
# check if directory exists
if [[ ! -d "$DIR" ]]; then
  echo "Directory not found: $DIR" >&2
  exit 1
fi

# Get files currently in the index for this tag
index_files=()
while IFS= read -r line; do
  [[ -n "$line" ]] && index_files+=("$line")
done < <(mindex --tag "$TAG" 2>/dev/null || true)

# Get actual .md files in the directory
disk_files=()
if [[ -d "$DIR" ]]; then
  while IFS= read -r f; do
    [[ -n "$f" ]] && disk_files+=("$f")
  done < <(find "$DIR" -maxdepth 1 -name '*.md' -type f)
fi

# Build associative arrays for fast lookup
declare -A index_set
for f in "${index_files[@]+"${index_files[@]}"}"; do
  index_set["$f"]=1
done

declare -A disk_set
for f in "${disk_files[@]+"${disk_files[@]}"}"; do
  disk_set["$f"]=1
done

# Find files to add (in directory but not in index)
to_add=()
for f in "${disk_files[@]+"${disk_files[@]}"}"; do
  if [[ -z "${index_set[$f]+_}" ]]; then
    to_add+=("$f")
  fi
done

# Find files to remove (in index but not on disk)
to_remove=()
for f in "${index_files[@]+"${index_files[@]}"}"; do
  if [[ -z "${disk_set[$f]+_}" ]]; then
    to_remove+=("$f")
  fi
done

# Remove missing entries
if [[ "$MODE" == "fix" ]]; then
  for f in "${to_remove[@]+"${to_remove[@]}"}"; do
    echo "rm: $f"
    mindex rm "$f" 2>/dev/null || true
  done
fi

# Add missing files
if [[ "$MODE" == "fix" ]]; then
  for f in "${to_add[@]+"${to_add[@]}"}"; do
    echo "add: $f"
    mindex add "$f" --tag "$TAG" 2>/dev/null || true
  done
fi

if [[ "$MODE" == "check" ]]; then
  echo "Check mode: would add ${#to_add[@]}, remove ${#to_remove[@]}."
else
  echo "Done. Added ${#to_add[@]}, removed ${#to_remove[@]}."
fi
