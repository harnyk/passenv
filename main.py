#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
passenv - profile-based secret injection:
- Reads a profile file (YAML or JSON) with env var to pass path mappings
- For each mapping, runs `pass show <path>` and takes the first non-empty line
- Exports environment variables with the specified names
- Does not overwrite existing env vars unless --overwrite is set
- If no command provided (after --), runs `env` by default, or use --cmd
"""

import argparse
import json
import os
import pathlib
import shlex
import subprocess
import sys
from typing import Dict, List

import yaml

def resolve_profile_path(profile_arg: str) -> str:
    """
    Resolve profile path. If the argument is not an existing file path,
    search for it in ~/.passenv/ with .yaml and .yml extensions.

    Args:
        profile_arg: Either a full path or a profile name

    Returns:
        Resolved absolute path to the profile file

    Raises:
        RuntimeError: If profile file cannot be found
    """
    path = pathlib.Path(profile_arg)

    # If it's an absolute path or has directory separators, use it as-is
    if path.is_absolute() or '/' in profile_arg:
        if path.exists():
            return str(path)
        raise RuntimeError(f"Profile file not found: {profile_arg}")

    # Otherwise, search in ~/.passenv/
    passenv_dir = pathlib.Path.home() / ".passenv"

    # Try the name as-is first (in case it has an extension)
    candidate = passenv_dir / profile_arg
    if candidate.exists():
        return str(candidate)

    # Try with extensions
    for ext in ['.yaml', '.yml']:
        candidate = passenv_dir / f"{profile_arg}{ext}"
        if candidate.exists():
            return str(candidate)

    # Not found anywhere
    raise RuntimeError(
        f"Profile '{profile_arg}' not found. Searched:\n"
        f"  - {passenv_dir / profile_arg}\n"
        f"  - {passenv_dir / (profile_arg + '.yaml')}\n"
        f"  - {passenv_dir / (profile_arg + '.yml')}"
    )

def load_profile(profile_path: str) -> Dict[str, str]:
    """
    Load profile from JSON or YAML file based on extension.
    Expected format: { "envs": { "ENV_VAR_NAME": "pass/path/to/secret", ... } }
    Returns the envs mapping dict.
    """
    path = pathlib.Path(profile_path)
    if not path.exists():
        raise RuntimeError(f"Profile file not found: {profile_path}")

    suffix = path.suffix.lower()
    try:
        with open(path, 'r') as f:
            if suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            elif suffix == '.json':
                data = json.load(f)
            else:
                raise RuntimeError(f"Unsupported profile format: {suffix}. Use .json, .yaml, or .yml")
    except Exception as e:
        raise RuntimeError(f"Failed to parse profile file: {e}")

    if not isinstance(data, dict) or 'envs' not in data:
        raise RuntimeError("Profile must contain 'envs' key with environment variable mappings")

    envs = data['envs']
    if not isinstance(envs, dict):
        raise RuntimeError("Profile 'envs' must be a dictionary mapping env var names to pass paths")

    return envs

def pass_show_first_nonempty(entry: str, pass_cmd: str = "pass") -> str:
    """
    Run `<pass_cmd> show <entry>` and return the first non-empty trimmed line.

    Args:
        entry: Path to the pass entry
        pass_cmd: Command to use for pass (default: "pass")
    """
    # Split the pass command to handle cases like "wsl pass"
    cmd_parts = shlex.split(pass_cmd)
    try:
        res = subprocess.run(
            cmd_parts + ["show", entry],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip() or e.stdout.strip() or str(e)
        raise RuntimeError(f"pass show failed for '{entry}': {msg}")
    for line in res.stdout.splitlines():
        s = line.strip()
        if s:
            return s
    raise RuntimeError(f"Empty secret for '{entry}'")

def build_env(profile_mapping: Dict[str, str], overwrite: bool, pass_cmd: str = "pass") -> Dict[str, str]:
    """
    Build environment variables from profile mapping.

    Args:
        profile_mapping: Dictionary mapping env var names to pass paths
        overwrite: Whether to overwrite existing environment variables
        pass_cmd: Command to use for pass (default: "pass")

    Returns:
        Dictionary of environment variables to set
    """
    env_vars: Dict[str, str] = {}

    for var_name, pass_path in profile_mapping.items():
        if not overwrite and var_name in os.environ:
            continue
        value = pass_show_first_nonempty(pass_path, pass_cmd)
        env_vars[var_name] = value

    return env_vars

def main():
    parser = argparse.ArgumentParser(description="Execute a command with env vars from pass profile.")
    parser.add_argument("--profile", required=True,
                        help="profile name (searches ~/.passenv/ with .yaml/.yml extensions) or full path to profile file")
    parser.add_argument("--overwrite", action="store_true",
                        help="overwrite existing environment variables")
    parser.add_argument("--dry-run", action="store_true",
                        help="print which VARs would be set (no values) and the command")
    parser.add_argument("--pass-cmd", dest="pass_cmd", default="pass",
                        help="command to use for pass (default: 'pass', e.g., 'wsl pass' for Windows)")
    parser.add_argument("--cmd", default=None,
                        help="command to run if nothing provided after -- (otherwise defaults to `env`)")
    parser.add_argument("remainder", nargs=argparse.REMAINDER,
                        help="command and args to run (use -- to separate)")
    args = parser.parse_args()

    # decide command
    cmd_and_args: List[str] = []
    if args.remainder:
        rem = args.remainder
        if rem and rem[0] == "--":
            rem = rem[1:]
        cmd_and_args = rem
    if not cmd_and_args:
        cmd_and_args = [args.cmd] if args.cmd else ["env"]

    # Resolve and load profile mapping
    try:
        resolved_profile = resolve_profile_path(args.profile)
        profile_mapping = load_profile(resolved_profile)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        env_to_set = build_env(profile_mapping, args.overwrite, args.pass_cmd)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        if env_to_set:
            print("Would set variables (values hidden):")
            for k in sorted(env_to_set.keys()):
                print(f"  {k}")
        else:
            print("No variables to set.")
        print("Command:", " ".join(shlex.quote(x) for x in cmd_and_args))
        return

    child_env = os.environ.copy()
    child_env.update(env_to_set)

    try:
        # Use subprocess.run instead of os.execvpe for better Windows compatibility
        # This ensures stdin/stdout/stderr are properly inherited on all platforms
        result = subprocess.run(cmd_and_args, env=child_env)
        sys.exit(result.returncode)
    except FileNotFoundError:
        print(f"[ERROR] Command not found: {cmd_and_args[0]}", file=sys.stderr)
        sys.exit(127)
    except Exception as e:
        print(f"[ERROR] Failed to run command: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
