# AGENTS.md - Guidelines for Agentic Coding

This file provides guidelines for agents working in the skilllib repository.

## Project Overview

This is a Python project (`skiller`) - a helper script to discover, install and manage skills for AI agents. The main source is in `skiller/skiller.py`.

## Build, Lint, and Test Commands

### Setup and Installation
```bash
cd skiller

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Unix/macOS

# Install in editable mode
uv pip install -e .

# Run the CLI
skiller
```

### Linting
Ruff is used for linting. Run:
```bash
ruff check .
```

### Type Checking
No type checker configured. Adding type hints is encouraged.

### Running Tests
No test framework configured yet. When adding tests:
```bash
# With pytest (recommended)
pytest

# Run a single test
pytest tests/test_specific_file.py::test_function_name
```

## Code Style Guidelines

### Imports
- Use standard library imports first, then third-party, then local
- Alphabetize imports within each group
- Use `import x` for standard library, `from x import y` for third-party and local when importing specific items
- Group imports with a single blank line between groups

```python
import argparse
import json
import os
import sys

import yaml
```

### Formatting
- Line length: 88 characters (ruff default)
- Use 4 spaces for indentation
- Blank lines: two blank lines between top-level definitions, one blank line between method definitions in a class
- No trailing whitespace

### Type Annotations
- Use type hints for function parameters and return values
- Prefer explicit types over `Any`
- Use `Optional[T]` or `T | None` for nullable types

```python
def load_config() -> dict:
    ...

def parse_frontmatter(file_path: str) -> dict | None:
    ...
```

### Naming Conventions
- **Functions**: `snake_case`
- **Variables**: `snake_case`
- **Constants**: `UPPER_SNAKE_CASE`
- **Classes**: `PascalCase`
- **Private methods/variables**: `_leading_underscore`
- Avoid single-character variable names except for trivial counters

### Error Handling
- Use specific exception types (`FileNotFoundError`, `JSONDecodeError`, `PermissionError`)
- Exit with `sys.exit(1)` for CLI errors
- Provide helpful error messages that include context
- Let unexpected exceptions propagate with tracebacks for debugging

```python
try:
    with open(config_path, 'r') as f:
        return json.load(f)
except FileNotFoundError:
    print(f"Error: Configuration file {config_path} not found.")
    sys.exit(1)
except json.JSONDecodeError:
    print(f"Error: Invalid JSON in {config_path}.")
    sys.exit(1)
```

### Docstrings
- Use triple double quotes for docstrings
- Write in present tense imperative mood
- Include args, returns, and raises sections for complex functions

```python
def load_config():
    """Load configuration from skiller_config.json."""
    ...
```

### CLI Design
- Use `argparse.ArgumentParser` for CLI
- Provide helpful epilog text
- Return early if no arguments provided (show help)

```python
parser = argparse.ArgumentParser(
    prog='skiller',
    description='Helper script to discover, install and manage skills for AI agents',
    epilog='Run without arguments to show help.'
)
```

### General Patterns
- Keep functions focused and under 50 lines when possible
- Use `__name__ == '__main__'` guard for CLI entry point
- Check preconditions early and return/fail fast
- Use `if __name__ == '__main__':` at module level (not inside functions)
- Prefer explicit over implicit
- Avoid magic numbers; use constants

## File Structure

```
skilllib/
├── AGENTS.md              <- You are here
├── README.md
├── .gitignore
├── dev/                   <- Development utilities
│   └── README-maker/
├── docs/                  <- Documentation fragments
│   ├── hais_proto.md.
│   └── qwen.md
└── skiller/               <- Main package
    ├── pyproject.toml     <- Project config
    ├── uv.lock
    ├── skiller.py         <- Main source
    ├── prd.md             <- Product requirements
    ├── README.md          <- Package documentation
    └── skiller_config.json
```

## Common Tasks

### Adding a New Command
1. Add argument in `main()` using `parser.add_argument()`
2. Implement handler function
3. Update `README.md` with usage documentation

### Modifying Configuration
Edit `skiller_config.json` - it is loaded at runtime via `load_config()`.

### Releasing a New Version
Update `version` in `skiller/pyproject.toml` following semantic versioning.
