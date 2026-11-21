"""Shared helpers: load skill scripts as modules without installing anything."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent


def load_script(skill: str, name: str):
    path = REPO / "skills" / skill / "scripts" / f"{name}.py"
    module_name = f"skill_{skill.replace('-', '_')}_{name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_script(skill: str, name: str, *args: str, stdin: str | None = None, cwd: Path | None = None):
    path = REPO / "skills" / skill / "scripts" / f"{name}.py"
    return subprocess.run(
        [sys.executable, str(path), *args], input=stdin, capture_output=True, text=True, cwd=cwd, timeout=60
    )


def write(root: Path, rel: str, content: str = "x\n") -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def git_available() -> bool:
    try:
        return subprocess.run(["git", "--version"], capture_output=True).returncode == 0
    except OSError:
        return False


requires_git = pytest.mark.skipif(not git_available(), reason="git not installed")


def git(cwd: Path, *args: str) -> str:
    env_args = [
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "-c",
        "tag.gpgsign=false",
    ]
    return subprocess.run(["git", *env_args, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout
