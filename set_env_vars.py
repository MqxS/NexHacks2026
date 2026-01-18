"""Simple .env loader and runner.

Usage:
  - Import and call `load()` from Python: `from set_env_vars import load; load()`
  - Run a command with the .env loaded:
      python set_env_vars.py --exec python main.py

This intentionally avoids external dependencies so it works in a fresh venv.
"""
from __future__ import annotations

import os
import subprocess
from typing import Dict


def _parse_dotenv(path: str) -> Dict[str, str]:
    pairs: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                if (val.startswith("\"") and val.endswith("\"")) or (
                    val.startswith("\'") and val.endswith("\'")):
                    val = val[1:-1]
                pairs[key] = val
    except FileNotFoundError:
        return {}
    return pairs


def load(path: str = ".env", override: bool = False) -> None:
    """Load key=value pairs from `path` into os.environ.

    Args:
        path: path to .env file (default: .env)
        override: if True, overwrite existing environment variables
    """
    for k, v in _parse_dotenv(path).items():
        if override or k not in os.environ:
            os.environ[k] = v


def run_command_with_env(cmd: list[str]) -> int:
    """Run a command (list form) with the current process environment and return exit code."""
    return subprocess.run(cmd, env=os.environ).returncode


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load .env and optionally run a command with it.")
    parser.add_argument("--env-file", "-e", default=".env", help="Path to .env file")
    parser.add_argument("--override", action="store_true", help="Override existing env vars")
    parser.add_argument("--exec", "-x", nargs=argparse.REMAINDER, help="Command to run with env loaded")
    args = parser.parse_args()

    load(args.env_file, override=args.override)

    if args.exec:
        # If user supplies a single string command, argparse.REMAINDER already gives list form.
        cmd = args.exec
        if not cmd:
            parser.error("--exec requires a command to run")
        rc = run_command_with_env(cmd)
        raise SystemExit(rc)
    else:
        print(f"Loaded environment from {args.env_file}")