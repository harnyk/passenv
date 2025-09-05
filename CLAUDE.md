# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `passenv`, a Python CLI tool that runs commands with environment variables populated from `pass` (password store) entries. It reads secrets from a specific pass folder (non-recursively), extracts the first non-empty line from each `.gpg` file, and exports them as environment variables with names based on the file basename converted to UPPER_SNAKE_CASE.

## Key Architecture

- **Single file application**: All functionality is contained in `main.py`
- **Entry point**: Configured in `pyproject.toml` as `passenv = "main:main"`
- **Core workflow**: 
  1. Find password store root (default: `~/.password-store`)
  2. List `.gpg` files in specified prefix folder (default: `secrets/`)
  3. Extract first non-empty line from each secret using `pass show`
  4. Convert filenames to env var names (basename → UPPER_SNAKE_CASE)
  5. Execute command with populated environment

## Common Commands

```bash
# Install in development mode
uv pip install -e .

# Run the tool
passenv [--prefix secrets] [--overwrite] [--dry-run] [--cmd command] [-- command args]

# Test the installation
passenv --dry-run

# Build distribution
uv build
```

## Key Functions

- `find_pass_store_root()`: Locates password store directory
- `list_pass_entries_strict()`: Non-recursive listing of `.gpg` files in prefix
- `pass_show_first_nonempty()`: Extracts first line from pass entries
- `to_env_name_from_basename()`: Converts filenames to env var names
- `build_env()`: Orchestrates environment variable creation
- `main()`: CLI argument parsing and command execution

## Development Notes

- Uses uv for package management (see `uv.lock`)
- Python 3.10+ required (see `.python-version`)
- No external dependencies beyond Python standard library
- Strict non-recursive behavior - only reads `.gpg` files directly in the specified prefix folder
- Uses `os.execvpe()` for command execution to replace current process