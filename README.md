# passenv

Run commands with environment variables populated from `pass` (password store) entries.

## Overview

`passenv` is a Python CLI tool that reads secrets from your `pass` password store using profile-based configuration and executes commands with those secrets available as environment variables. It provides a secure way to inject credentials into your development workflow without hardcoding them.

### Key Features

- **Profile-based**: Explicit mapping of environment variables to pass paths via YAML or JSON
- **Secure**: Uses `pass show` to decrypt secrets, respects existing environment variables
- **Flexible**: Load secrets from any pass paths, custom command specification, and dry-run mode
- **Simple**: Single-file implementation with minimal dependencies (only PyYAML)

## Installation

### Quick Start with uvx (Recommended)

Run directly from GitHub without installation:

```bash
uvx --from git+https://github.com/harnyk/passenv.git passenv --help
```

### Install as Tool

Install permanently with uv:

```bash
uv tool install git+https://github.com/harnyk/passenv.git
```

### Development Installation

Clone and install in development mode:

```bash
git clone https://github.com/harnyk/passenv.git
cd passenv
uv pip install -e .
```

## Usage

### Create a Profile File

Create a profile file (YAML or JSON) that maps environment variable names to pass paths:

**YAML format (`my-profile.yaml`):**
```yaml
envs:
  DATABASE_URL: myapp/prod/database_url
  API_KEY: myapp/prod/api_key
  JWT_SECRET: shared/jwt_secret
```

**JSON format (`my-profile.json`):**
```json
{
  "envs": {
    "DATABASE_URL": "myapp/prod/database_url",
    "API_KEY": "myapp/prod/api_key",
    "JWT_SECRET": "shared/jwt_secret"
  }
}
```

### Run Commands

```bash
# Run with profile
passenv --profile my-profile.yaml -- your-command arg1 arg2

# See what would be set
passenv --profile my-profile.yaml --dry-run

# Overwrite existing env vars
passenv --profile my-profile.yaml --overwrite -- your-command
```

### Command-Line Options

```bash
passenv --profile PROFILE [OPTIONS] [-- COMMAND [ARGS...]]

Required:
  --profile PATH    Profile file (.json, .yaml, .yml) with env var mappings

Options:
  --overwrite       Overwrite existing environment variables
  --dry-run         Show what variables would be set
  --cmd TEXT        Default command if none provided after --
  --help           Show help message
```

## How It Works

1. **Load Profile**: Reads the profile file (YAML or JSON) containing env var to pass path mappings
2. **Extract Values**: For each mapping, runs `pass show <path>` and takes the first non-empty line
3. **Set Variables**: Creates environment variables with the exact names specified in the profile
4. **Execute Command**: Runs your command with the populated environment

### Example

Given this profile file `app.yaml`:
```yaml
envs:
  DATABASE_URL: myapp/prod/db_url
  API_KEY: shared/services/api_key
  JWT_SECRET: shared/jwt_secret
```

Running `passenv --profile app.yaml --dry-run` would show:
```
Would set variables (values hidden):
  API_KEY
  DATABASE_URL
  JWT_SECRET
Command: env
```

## Examples

### Development Workflow

```bash
# Start development server with production secrets
passenv --profile prod.yaml -- npm run dev

# Run tests with test environment secrets
passenv --profile test.yaml -- pytest

# Deploy with deployment credentials
passenv --profile deploy.yaml -- ./deploy.sh

# Run Python app with specific secrets
passenv --profile app.yaml -- python app.py
```

### One-liner with uvx

```bash
# No installation required - run directly from GitHub
uvx --from git+https://github.com/harnyk/passenv.git passenv --profile my-profile.yaml -- python app.py
```

### Profile Benefits

- **Explicit control**: Choose exactly which secrets to load and their env var names
- **Cross-folder support**: Load secrets from different pass folders in one profile
- **Flexible naming**: Use any env var name that matches your application's needs
- **Documentation**: Profile files serve as documentation of which secrets your app requires
- **Version control friendly**: Profile files (without values) can be committed to show required secrets

## Requirements

- Python 3.10+
- `pass` (password store) installed and configured
- Password store with secrets in `.gpg` files

## Security Notes

- Values are never logged or displayed (except in dry-run mode where values are hidden)
- Existing environment variables are preserved unless `--overwrite` is used
- Uses `pass show` which respects your GPG agent configuration
- Process execution replaces current process, preventing memory leaks

## License

This project is open source. See the repository for license details.