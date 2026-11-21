#!/usr/bin/env python3
"""Generate a GitHub Actions CI workflow for a Python, Node.js or PHP project.

The script inspects the project (manifests, lockfiles, dev tools, scripts) and
prints a workflow with a version matrix, dependency caching, least-privilege
permissions and concurrency cancelling. It prints to stdout unless --output is
given, and refuses to overwrite an existing file without --force.

  gen_ci.py detect [PATH] [--json]
  gen_ci.py generate [PATH] [--lang auto|python|node|php] [--versions 3.12,3.13]
                    [--os ubuntu-latest,windows-latest] [--output .github/workflows/ci.yml]

Exit codes: 0 = ok, 1 = nothing to generate (unknown project type, file exists), 2 = usage error.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tomllib
from pathlib import Path

ACTIONS = {
    "checkout": "actions/checkout@v7",
    "setup-python": "actions/setup-python@v7",
    "setup-node": "actions/setup-node@v7",
    "cache": "actions/cache@v6",
    "setup-php": "shivammathur/setup-php@v2",
    "pnpm": "pnpm/action-setup@v6",
}
DEFAULT_VERSIONS = {
    "python": ["3.11", "3.12", "3.13", "3.14"],
    "node": ["22", "24"],
    "php": ["8.2", "8.3", "8.4"],
}
NPM_DEFAULT_TEST = 'echo "Error: no test specified" && exit 1'


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def detect_python(root: Path) -> dict | None:
    pyproject = root / "pyproject.toml"
    reqs = root / "requirements.txt"
    if not (pyproject.exists() or reqs.exists() or (root / "setup.py").exists() or (root / "setup.cfg").exists()):
        return None
    info: dict = {"lang": "python", "install": [], "lint": [], "test": "", "cache_paths": []}
    data: dict = {}
    if pyproject.exists():
        try:
            data = tomllib.loads(_read(pyproject))
        except tomllib.TOMLDecodeError:
            data = {}
    text_all = _read(pyproject) + _read(reqs) + _read(root / "requirements-dev.txt") + _read(root / "setup.cfg")
    extras = (data.get("project") or {}).get("optional-dependencies") or {}
    groups = data.get("dependency-groups") or {}
    dev_extra = next((name for name in ("dev", "test", "tests") if name in extras), None)
    has_project = "project" in data or (root / "setup.py").exists()

    install = ["python -m pip install --upgrade pip"]
    if (root / "requirements-dev.txt").exists():
        install.append("pip install -r requirements-dev.txt")
        info["cache_paths"].append("requirements-dev.txt")
    if reqs.exists():
        install.append("pip install -r requirements.txt")
        info["cache_paths"].append("requirements.txt")
    if has_project:
        install.append(f'pip install -e ".[{dev_extra}]"' if dev_extra else "pip install -e .")
    if "dev" in groups:
        install.append("pip install --group dev")
    if pyproject.exists():
        info["cache_paths"].append("pyproject.toml")
    info["install"] = install

    tools = data.get("tool") or {}
    if "ruff" in tools or re.search(r"\bruff\b", text_all):
        info["lint"] = ["ruff check .", "ruff format --check ."]
    elif "flake8" in text_all:
        info["lint"] = ["flake8 ."]
    if "mypy" in tools:
        info["lint"].append("mypy .")
    if "pytest" in text_all or "pytest" in tools or (root / "tests").is_dir():
        info["test"] = "pytest"
    else:
        info["test"] = "python -m unittest discover"
    needs = [
        t.split()[0] for t in info["lint"] + [info["test"]] if t.split()[0] in ("ruff", "flake8", "mypy", "pytest")
    ]
    if needs and not re.search(r"\b(" + "|".join(sorted(set(needs))) + r")\b", text_all):
        info["install"].append("pip install " + " ".join(sorted(set(needs))))
    return info


def detect_node(root: Path) -> dict | None:
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return None
    try:
        pkg = json.loads(_read(pkg_path))
    except json.JSONDecodeError:
        pkg = {}
    scripts = pkg.get("scripts") or {}
    if (root / "pnpm-lock.yaml").exists():
        pm, install, lock = "pnpm", "pnpm install --frozen-lockfile", "pnpm-lock.yaml"
    elif (root / "yarn.lock").exists():
        pm, install, lock = "yarn", "yarn install --frozen-lockfile", "yarn.lock"
    elif (root / "package-lock.json").exists() or (root / "npm-shrinkwrap.json").exists():
        pm, install, lock = "npm", "npm ci", "package-lock.json"
    else:
        pm, install, lock = "npm", "npm install", ""
    run = "npm run" if pm == "npm" else pm
    steps = []
    for name in ("lint", "typecheck", "build"):
        if name in scripts:
            steps.append(f"{run} {name}")
    test = scripts.get("test", "")
    if test and test.strip() != NPM_DEFAULT_TEST:
        steps.append("npm test" if pm == "npm" else f"{pm} test")
    return {"lang": "node", "package_manager": pm, "install": [install], "steps": steps, "lockfile": lock}


def detect_php(root: Path) -> dict | None:
    composer_path = root / "composer.json"
    if not composer_path.exists():
        return None
    try:
        composer = json.loads(_read(composer_path))
    except json.JSONDecodeError:
        composer = {}
    dev = composer.get("require-dev") or {}
    scripts = composer.get("scripts") or {}
    steps = []
    if "phpstan/phpstan" in dev:
        steps.append("vendor/bin/phpstan analyse --no-progress")
    if "squizlabs/php_codesniffer" in dev:
        steps.append("vendor/bin/phpcs")
    if "friendsofphp/php-cs-fixer" in dev:
        steps.append("vendor/bin/php-cs-fixer fix --dry-run --diff")
    if "test" in scripts:
        steps.append("composer test")
    elif "phpunit/phpunit" in dev:
        steps.append("vendor/bin/phpunit")
    elif "pestphp/pest" in dev:
        steps.append("vendor/bin/pest")
    return {"lang": "php", "install": ["composer install --no-interaction --no-progress --prefer-dist"], "steps": steps}


DETECTORS = {"python": detect_python, "node": detect_node, "php": detect_php}


def detect(root: Path) -> list[dict]:
    return [info for fn in DETECTORS.values() if (info := fn(root))]


def _q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _run_block(commands: list[str], indent: str) -> list[str]:
    if len(commands) == 1:
        return [f"{indent}run: {commands[0]}"]
    return [f"{indent}run: |"] + [f"{indent}  {c}" for c in commands]


def header(name: str, branches: list[str]) -> list[str]:
    return [
        f"name: {name}",
        "",
        "on:",
        "  push:",
        f"    branches: [{', '.join(branches)}]",
        "  pull_request:",
        "  workflow_dispatch:",
        "",
        "permissions:",
        "  contents: read",
        "",
        "concurrency:",
        "  group: ${{ github.workflow }}-${{ github.ref }}",
        "  cancel-in-progress: true",
        "",
        "jobs:",
    ]


def matrix_lines(key: str, versions: list[str], oses: list[str]) -> list[str]:
    lines = [
        "    runs-on: ${{ matrix.os }}",
        "    strategy:",
        "      fail-fast: false",
        "      matrix:",
        f"        os: [{', '.join(oses)}]",
        f"        {key}: [{', '.join(_q(v) for v in versions)}]",
    ]
    return lines


def python_job(info: dict, versions: list[str], oses: list[str]) -> list[str]:
    lines = ["  test:", "    name: Python ${{ matrix.python-version }} on ${{ matrix.os }}"]
    lines += matrix_lines("python-version", versions, oses)
    lines += [
        "    steps:",
        f"      - uses: {ACTIONS['checkout']}",
        f"      - uses: {ACTIONS['setup-python']}",
        "        with:",
        "          python-version: ${{ matrix.python-version }}",
        "          cache: pip",
    ]
    if info["cache_paths"]:
        if len(info["cache_paths"]) == 1:
            lines.append(f"          cache-dependency-path: {info['cache_paths'][0]}")
        else:
            lines.append("          cache-dependency-path: |")
            lines += [f"            {p}" for p in info["cache_paths"]]
    lines += ["      - name: Install dependencies", *_run_block(info["install"], "        ")]
    if info["lint"]:
        lines += ["      - name: Lint", *_run_block(info["lint"], "        ")]
    lines += ["      - name: Test", f"        run: {info['test']}"]
    return lines


def node_job(info: dict, versions: list[str], oses: list[str]) -> list[str]:
    lines = ["  test:", "    name: Node ${{ matrix.node-version }} on ${{ matrix.os }}"]
    lines += matrix_lines("node-version", versions, oses)
    lines += ["    steps:", f"      - uses: {ACTIONS['checkout']}"]
    if info["package_manager"] == "pnpm":
        lines.append(f"      - uses: {ACTIONS['pnpm']}")
    lines += [
        f"      - uses: {ACTIONS['setup-node']}",
        "        with:",
        "          node-version: ${{ matrix.node-version }}",
    ]
    if info["lockfile"]:
        lines.append(f"          cache: {info['package_manager']}")
    lines += ["      - name: Install dependencies", f"        run: {info['install'][0]}"]
    for step in info["steps"]:
        label = step.split()[-1].capitalize()
        lines += [f"      - name: {label}", f"        run: {step}"]
    if not info["steps"]:
        lines += ["      - name: Test", "        run: echo 'Add a \"test\" script to package.json' && exit 1"]
    return lines


def php_job(info: dict, versions: list[str], oses: list[str]) -> list[str]:
    lines = ["  test:", "    name: PHP ${{ matrix.php-version }} on ${{ matrix.os }}"]
    lines += matrix_lines("php-version", versions, oses)
    lines += [
        "    steps:",
        f"      - uses: {ACTIONS['checkout']}",
        f"      - uses: {ACTIONS['setup-php']}",
        "        with:",
        "          php-version: ${{ matrix.php-version }}",
        "          coverage: none",
        "          tools: composer:v2",
        "      - name: Get Composer cache directory",
        "        id: composer-cache",
        "        shell: bash",
        '        run: echo "dir=$(composer config cache-files-dir)" >> "$GITHUB_OUTPUT"',
        f"      - uses: {ACTIONS['cache']}",
        "        with:",
        "          path: ${{ steps.composer-cache.outputs.dir }}",
        "          key: ${{ runner.os }}-php${{ matrix.php-version }}-composer-${{ hashFiles('**/composer.lock', '**/composer.json') }}",
        "          restore-keys: ${{ runner.os }}-php${{ matrix.php-version }}-composer-",
        "      - name: Validate composer.json",
        "        run: composer validate --strict",
        "      - name: Install dependencies",
        f"        run: {info['install'][0]}",
    ]
    for step in info["steps"]:
        label = "Test" if "test" in step or "phpunit" in step or "pest" in step else "Static analysis"
        lines += [f"      - name: {label}", f"        run: {step}"]
    return lines


JOBS = {"python": python_job, "node": node_job, "php": php_job}


def generate(info: dict, versions: list[str] | None, oses: list[str], branches: list[str]) -> str:
    lang = info["lang"]
    lines = header("CI", branches) + JOBS[lang](info, versions or DEFAULT_VERSIONS[lang], oses)
    return "\n".join(lines) + "\n"


def _csv(value: str | None) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()] if value else []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate a GitHub Actions CI workflow for Python, Node.js or PHP.")
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("detect", help="show what the generator detected")
    d.add_argument("path", nargs="?", default=".")
    d.add_argument("--json", action="store_true")
    g = sub.add_parser("generate", help="print (or write) the workflow")
    g.add_argument("path", nargs="?", default=".")
    g.add_argument("--lang", choices=["auto", *DETECTORS], default="auto")
    g.add_argument("--versions", help="comma-separated runtime versions for the matrix")
    g.add_argument("--os", default="ubuntu-latest", help="comma-separated runners (default: ubuntu-latest)")
    g.add_argument("--branches", default="main", help="branches that trigger on push (default: main)")
    g.add_argument("--output", help="write to this file instead of stdout")
    g.add_argument("--force", action="store_true", help="overwrite --output if it exists")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.is_dir():
        print(f"error: {root} is not a directory", file=sys.stderr)
        return 2
    found = detect(root)

    if args.cmd == "detect":
        if args.json:
            print(json.dumps(found, indent=2))
        elif not found:
            print("No Python, Node.js or PHP project detected.")
        else:
            for info in found:
                print(json.dumps(info))
        return 0 if found else 1

    if args.lang == "auto":
        if not found:
            print(
                "error: no pyproject.toml/requirements.txt, package.json or composer.json found; pass --lang",
                file=sys.stderr,
            )
            return 1
        if len(found) > 1:
            langs = ", ".join(i["lang"] for i in found)
            print(
                f"note: several project types found ({langs}); using {found[0]['lang']}. Pass --lang to choose.",
                file=sys.stderr,
            )
        info = found[0]
    else:
        info = DETECTORS[args.lang](root)
        if info is None:
            print(f"error: no {args.lang} manifest found in {root}", file=sys.stderr)
            return 1

    workflow = generate(
        info, _csv(args.versions) or None, _csv(args.os) or ["ubuntu-latest"], _csv(args.branches) or ["main"]
    )
    if args.output:
        out = Path(args.output)
        if out.exists() and not args.force:
            print(f"error: {out} exists; pass --force to overwrite", file=sys.stderr)
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(workflow, encoding="utf-8")
        print(f"wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(workflow)
    return 0


if __name__ == "__main__":
    sys.exit(main())
