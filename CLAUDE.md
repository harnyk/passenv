# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `passenv`, a Python CLI tool that runs commands with environment variables populated from `pass` (password store) entries using profile-based configuration. It reads a profile file (YAML or JSON) that explicitly maps environment variable names to pass paths, extracts the first non-empty line from each secret, and executes commands with those variables set.

## Key Architecture

- **Single file application**: All functionality is contained in `main.py`
- **Entry point**: Configured in `pyproject.toml` as `passenv = "main:main"`
- **Profile-based**: Uses YAML or JSON files to define env var → pass path mappings
- **Core workflow**:
  1. Load profile file (YAML or JSON)
  2. Extract env var name → pass path mappings from the `envs` key
  3. For each mapping, run `pass show <path>` and extract first non-empty line
  4. Execute command with populated environment variables

## Common Commands

```bash
# Install globally as a CLI tool (editable mode for development)
uv tool install --force --editable .

# Install in development mode (alternative)
uv pip install -e .

# Run the tool
passenv --profile my-profile.yaml [--overwrite] [--dry-run] [--cmd command] [-- command args]

# Test the installation
passenv --profile test-profile.yaml --dry-run

# Build distribution
uv build
```

## Key Functions

- `load_profile(profile_path)`: Loads and validates profile file (JSON or YAML)
- `pass_show_first_nonempty(entry)`: Extracts first non-empty line from pass entries
- `build_env(profile_mapping, overwrite)`: Creates env vars from profile mappings
- `main()`: CLI argument parsing and command execution

## Development Notes

- Uses uv for package management (see `uv.lock`)
- Python 3.10+ required (see `.python-version`)
- Single external dependency: PyYAML
- Profile files must contain an `envs` key with a dictionary of env var → pass path mappings
- Uses `subprocess.run()` for command execution with proper stdin/stdout/stderr inheritance (Windows-compatible)
- Supports both YAML (.yaml, .yml) and JSON (.json) profile formats