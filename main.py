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

def pass_show_first_nonempty(entry: str) -> str:
    """
    Run `pass show <entry>` and return the first non-empty trimmed line.
    """
    try:
        res = subprocess.run(
            ["pass", "show", entry],
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

def build_env(profile_mapping: Dict[str, str], overwrite: bool) -> Dict[str, str]:
    """
    Build environment variables from profile mapping.

    Args:
        profile_mapping: Dictionary mapping env var names to pass paths
        overwrite: Whether to overwrite existing environment variables

    Returns:
        Dictionary of environment variables to set
    """
    env_vars: Dict[str, str] = {}

    for var_name, pass_path in profile_mapping.items():
        if not overwrite and var_name in os.environ:
            continue
        value = pass_show_first_nonempty(pass_path)
        env_vars[var_name] = value

    return env_vars

def main():
    parser = argparse.ArgumentParser(description="Execute a command with env vars from pass profile.")
    parser.add_argument("--profile", required=True,
                        help="path to profile file (.json, .yaml, .yml) defining env var to pass path mappings")
    parser.add_argument("--overwrite", action="store_true",
                        help="overwrite existing environment variables")
    parser.add_argument("--dry-run", action="store_true",
                        help="print which VARs would be set (no values) and the command")
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

    # Load profile mapping
    try:
        profile_mapping = load_profile(args.profile)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        env_to_set = build_env(profile_mapping, args.overwrite)
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
        os.execvpe(cmd_and_args[0], cmd_and_args, child_env)
    except FileNotFoundError:
        print(f"[ERROR] Command not found: {cmd_and_args[0]}", file=sys.stderr)
        sys.exit(127)
    except Exception as e:
        print(f"[ERROR] Failed to exec command: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
