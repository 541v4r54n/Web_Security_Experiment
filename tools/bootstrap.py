from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
REQUIREMENTS = ROOT / "requirements.txt"


def _venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def _run(cmd: list[str]) -> int:
    proc = subprocess.run(cmd, cwd=str(ROOT))
    return int(proc.returncode)


def ensure_venv(*, clean: bool) -> Path:
    venv_python = _venv_python()
    if clean and VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)

    if venv_python.exists():
        return venv_python

    # If a venv exists but doesn't match the current OS layout (e.g., Windows venv on Linux),
    # recreate it for the current platform.
    if VENV_DIR.exists():
        shutil.rmtree(VENV_DIR)

    if _run([sys.executable, "-m", "venv", str(VENV_DIR)]) != 0:
        raise SystemExit(1)

    venv_python = _venv_python()
    if not venv_python.exists():
        print(f"venv python not found: {venv_python}", file=sys.stderr)
        raise SystemExit(1)

    if _run([str(venv_python), "-m", "pip", "install", "-U", "pip"]) != 0:
        raise SystemExit(1)
    if _run([str(venv_python), "-m", "pip", "install", "-r", str(REQUIREMENTS)]) != 0:
        raise SystemExit(1)
    return venv_python


def cmd_setup(args: argparse.Namespace) -> int:
    venv_python = ensure_venv(clean=bool(args.clean_venv))
    if _run([str(venv_python), "-m", "websec_app", "init-db"]) != 0:
        return 1
    if _run([str(venv_python), "-m", "websec_app", "gen-cert"]) != 0:
        return 1
    return 0


def cmd_self_check(args: argparse.Namespace) -> int:
    venv_python = ensure_venv(clean=bool(args.clean_venv))
    return _run([str(venv_python), "-m", "websec_app", "self-check"])


def cmd_run_http(args: argparse.Namespace) -> int:
    venv_python = ensure_venv(clean=False)
    return _run(
        [
            str(venv_python),
            "-m",
            "websec_app",
            "run",
            "--host",
            str(args.host),
            "--port",
            str(args.port),
        ]
    )


def cmd_run_https(args: argparse.Namespace) -> int:
    venv_python = ensure_venv(clean=False)
    return _run(
        [
            str(venv_python),
            "-m",
            "websec_app",
            "run",
            "--https",
            "--host",
            str(args.host),
            "--port",
            str(args.port),
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="bootstrap.py", description="WebSec Lab setup/run helper")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_setup = sub.add_parser("setup", help="Create venv, install deps, init db, gen https cert")
    p_setup.add_argument("--clean-venv", action="store_true", help="Remove and recreate .venv")
    p_setup.set_defaults(func=cmd_setup)

    p_check = sub.add_parser("self-check", help="Sanity check local environment")
    p_check.add_argument("--clean-venv", action="store_true", help="Remove and recreate .venv")
    p_check.set_defaults(func=cmd_self_check)

    p_http = sub.add_parser("run-http", help="Run on HTTP (default http://127.0.0.1:5000)")
    p_http.add_argument("--host", default="127.0.0.1")
    p_http.add_argument("--port", default=5000, type=int)
    p_http.set_defaults(func=cmd_run_http)

    p_https = sub.add_parser("run-https", help="Run on HTTPS (default https://127.0.0.1:5443)")
    p_https.add_argument("--host", default="127.0.0.1")
    p_https.add_argument("--port", default=5443, type=int)
    p_https.set_defaults(func=cmd_run_https)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

