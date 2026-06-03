# Agent Configuration

## Project Overview
A Python package (`mindex`) providing SQLite FTS5-based search functionality with a wiki-style knowledge base. Uses `llm-wiki` MCP server for agent interactions.

## Defaults

### Wiki
- Use `llm-wiki` with index directory set to the project root.

### Tooling
- Use `jq` for JSON parsing.
- Use `uv` for Python package management and execution.

## Project Structure
```
.
├── src/mindex/          # Main package source code
├── src/tests/           # Test suite
├── skills/              # Agent skill definitions
├── tmp/                 # Temporary/artifact directory
├── pyproject.toml       # Project configuration & dependencies
└── uv.lock              # Dependency lock file
```

## Commands
```bash
uv run pytest              # Run tests
uv run pytest -v           # Verbose output
uv run pytest --cov        # With coverage
uv run ruff check .        # Lint
uv run ruff format .       # Format
```

## Code Style
- Follow PEP 8 for Python code.
- Use type hints in function signatures.
- Write docstrings for public functions and classes.

## Testing
- Create **positive** test cases: verify expected behavior under normal conditions.
- Create **negative** test cases: verify correct failure handling for invalid inputs.
- Cover **edge cases**: empty inputs, boundary values, unusual characters, and error conditions.

## Boundaries
- Do not modify files outside the project scope without explicit approval.
- Do not commit secrets, credentials, or sensitive data.
