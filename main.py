#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
passenv (strict, non-recursive):
- Reads secrets only from the exact pass folder <prefix> (no subfolders).
- For each *.gpg in that folder, runs `pass show <entry>` and takes the first non-empty line.
- Exports env vars named after the basename of the file (UPPER_SNAKE).
- Fails if the prefix doesn't exist or contains no *.gpg files.
- Does not overwrite existing env vars unless --overwrite is set.
- If no command provided (after --), runs `env` by default, or use --cmd.
"""

import argparse
import os
import pathlib
import shlex
import subprocess
import sys
from typing import Dict, List

def find_pass_store_root() -> pathlib.Path:
    root = os.environ.get("PASSWORD_STORE_DIR", os.path.expanduser("~/.password-store"))
    return pathlib.Path(root)

def list_pass_entries_strict(root: pathlib.Path, prefix: str) -> List[str]:
    """
    Return pass entry names (relative to store root without .gpg) for *.gpg
    directly under <root>/<prefix>. No recursion.
    """
    base = (root / prefix).resolve()
    if not base.exists() or not base.is_dir():
        raise RuntimeError(f"Prefix '{prefix}' not found in password store at '{base}'")
    entries: List[str] = []
    for p in sorted(base.glob("*.gpg")):  # non-recursive
        rel = p.relative_to(root).as_posix()
        entries.append(rel[:-4])  # strip .gpg
    if not entries:
        raise RuntimeError(f"No secrets found under prefix '{prefix}' (no *.gpg files)")
    return entries

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

def to_env_name_from_basename(entry: str) -> str:
    """
    Convert pass entry path to env var using only the basename.
    secrets/claude/JIRA_TOKEN -> JIRA_TOKEN
    """
    base = pathlib.Path(entry).name
    up = base.upper()
    return "".join(ch if (ch.isalnum() or ch == "_") else "_" for ch in up)

def build_env(store_root: pathlib.Path, prefix: str, overwrite: bool) -> Dict[str, str]:
    env_vars: Dict[str, str] = {}
    entries = list_pass_entries_strict(store_root, prefix)
    for entry in entries:
        var_name = to_env_name_from_basename(entry)
        if not overwrite and var_name in os.environ:
            continue
        value = pass_show_first_nonempty(entry)
        env_vars[var_name] = value
    return env_vars

def main():
    parser = argparse.ArgumentParser(description="Execute a command with env vars from pass (non-recursive).")
    parser.add_argument("--prefix", default="secrets",
                        help="pass path prefix (exact folder under the store; default: secrets)")
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

    store_root = find_pass_store_root()
    try:
        env_to_set = build_env(store_root, args.prefix, args.overwrite)
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
