import json

import pytest

from conftest import load_script, run_script, write

gc = load_script("github-actions-ci", "gen_ci")
yaml = pytest.importorskip("yaml")

PYPROJECT = """
[project]
name = "demo"
version = "0.1.0"

[project.optional-dependencies]
dev = ["pytest", "ruff"]

[tool.ruff]
line-length = 100
"""


def parse(text):
    data = yaml.safe_load(text)
    # PyYAML (YAML 1.1) reads the bare key `on` as True.
    return data, data.get("on", data.get(True))


def test_python_detection_and_workflow(tmp_path):
    write(tmp_path, "pyproject.toml", PYPROJECT)
    info = gc.detect_python(tmp_path)
    assert info["install"][-1] == 'pip install -e ".[dev]"'
    assert info["lint"] == ["ruff check .", "ruff format --check ."]
    assert info["test"] == "pytest"
    wf, on = parse(gc.generate(info, None, ["ubuntu-latest"], ["main"]))
    assert on["push"]["branches"] == ["main"]
    assert wf["permissions"] == {"contents": "read"}
    assert wf["concurrency"]["cancel-in-progress"] is True
    job = wf["jobs"]["test"]
    assert job["strategy"]["matrix"]["python-version"] == gc.DEFAULT_VERSIONS["python"]
    setup = job["steps"][1]
    assert setup["uses"] == gc.ACTIONS["setup-python"]
    assert setup["with"]["cache"] == "pip"
    assert setup["with"]["cache-dependency-path"] == "pyproject.toml"
    assert job["steps"][-1]["run"] == "pytest"


def test_python_requirements_without_tools(tmp_path):
    write(tmp_path, "requirements.txt", "requests\n")
    info = gc.detect_python(tmp_path)
    assert "pip install -r requirements.txt" in info["install"]
    assert info["test"] == "python -m unittest discover"
    write(tmp_path, "tests/test_x.py", "")
    info = gc.detect_python(tmp_path)
    assert info["test"] == "pytest"
    assert info["install"][-1] == "pip install pytest"


def test_python_multiple_cache_paths(tmp_path):
    write(tmp_path, "pyproject.toml", PYPROJECT)
    write(tmp_path, "requirements-dev.txt", "pytest\n")
    info = gc.detect_python(tmp_path)
    wf, _ = parse(gc.generate(info, ["3.13"], ["ubuntu-latest", "windows-latest"], ["main", "develop"]))
    setup = wf["jobs"]["test"]["steps"][1]
    assert setup["with"]["cache-dependency-path"].split() == ["requirements-dev.txt", "pyproject.toml"]
    assert wf["jobs"]["test"]["strategy"]["matrix"]["os"] == ["ubuntu-latest", "windows-latest"]


@pytest.mark.parametrize(
    ("lockfile", "pm", "install"),
    [
        ("package-lock.json", "npm", "npm ci"),
        ("pnpm-lock.yaml", "pnpm", "pnpm install --frozen-lockfile"),
        ("yarn.lock", "yarn", "yarn install --frozen-lockfile"),
    ],
)
def test_node_package_managers(tmp_path, lockfile, pm, install):
    write(tmp_path, "package.json", json.dumps({"scripts": {"lint": "eslint .", "test": "vitest run", "build": "tsc"}}))
    write(tmp_path, lockfile, "")
    info = gc.detect_node(tmp_path)
    assert info["package_manager"] == pm
    wf, _ = parse(gc.generate(info, None, ["ubuntu-latest"], ["main"]))
    steps = wf["jobs"]["test"]["steps"]
    uses = [s.get("uses") for s in steps if "uses" in s]
    assert (gc.ACTIONS["pnpm"] in uses) == (pm == "pnpm")
    setup = next(s for s in steps if s.get("uses") == gc.ACTIONS["setup-node"])
    assert setup["with"]["cache"] == pm
    runs = [s.get("run") for s in steps if "run" in s]
    assert runs[0] == install
    assert any(r.endswith("lint") for r in runs) and any(r.endswith("test") for r in runs)


def test_node_default_test_script_ignored_and_no_lockfile(tmp_path):
    write(tmp_path, "package.json", json.dumps({"scripts": {"test": gc.NPM_DEFAULT_TEST}}))
    info = gc.detect_node(tmp_path)
    assert info["steps"] == [] and info["install"] == ["npm install"]
    wf, _ = parse(gc.generate(info, ["24"], ["ubuntu-latest"], ["main"]))
    setup = next(s for s in wf["jobs"]["test"]["steps"] if s.get("uses") == gc.ACTIONS["setup-node"])
    assert "cache" not in setup["with"]


def test_php_workflow(tmp_path):
    composer = {"require-dev": {"phpunit/phpunit": "^11", "phpstan/phpstan": "^2"}}
    write(tmp_path, "composer.json", json.dumps(composer))
    info = gc.detect_php(tmp_path)
    assert info["steps"] == ["vendor/bin/phpstan analyse --no-progress", "vendor/bin/phpunit"]
    wf, _ = parse(gc.generate(info, None, ["ubuntu-latest"], ["main"]))
    steps = wf["jobs"]["test"]["steps"]
    assert any(s.get("uses") == gc.ACTIONS["cache"] for s in steps)
    assert wf["jobs"]["test"]["strategy"]["matrix"]["php-version"] == gc.DEFAULT_VERSIONS["php"]
    composer["scripts"] = {"test": "phpunit"}
    write(tmp_path, "composer.json", json.dumps(composer))
    assert gc.detect_php(tmp_path)["steps"][-1] == "composer test"


def test_detect_multiple(tmp_path):
    write(tmp_path, "pyproject.toml", PYPROJECT)
    write(tmp_path, "package.json", "{}")
    assert [i["lang"] for i in gc.detect(tmp_path)] == ["python", "node"]


def test_cli_generate_and_overwrite_protection(tmp_path):
    write(tmp_path, "package.json", json.dumps({"scripts": {"test": "jest"}}))
    out = tmp_path / ".github/workflows/ci.yml"
    proc = run_script("github-actions-ci", "gen_ci", "generate", str(tmp_path), "--output", str(out))
    assert proc.returncode == 0 and out.exists()
    again = run_script("github-actions-ci", "gen_ci", "generate", str(tmp_path), "--output", str(out))
    assert again.returncode == 1 and "exists" in again.stderr
    forced = run_script("github-actions-ci", "gen_ci", "generate", str(tmp_path), "--output", str(out), "--force")
    assert forced.returncode == 0


def test_cli_unknown_project(tmp_path):
    assert run_script("github-actions-ci", "gen_ci", "generate", str(tmp_path)).returncode == 1
    assert run_script("github-actions-ci", "gen_ci", "generate", str(tmp_path), "--lang", "php").returncode == 1
    assert run_script("github-actions-ci", "gen_ci", "detect", str(tmp_path)).returncode == 1
    assert run_script("github-actions-ci", "gen_ci", "detect", str(tmp_path / "nope")).returncode == 2


def test_cli_versions_flag(tmp_path):
    write(tmp_path, "composer.json", "{}")
    proc = run_script("github-actions-ci", "gen_ci", "generate", str(tmp_path), "--versions", "8.3, 8.4")
    wf, _ = parse(proc.stdout)
    assert wf["jobs"]["test"]["strategy"]["matrix"]["php-version"] == ["8.3", "8.4"]
