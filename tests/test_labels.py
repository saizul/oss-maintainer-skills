import json
import shlex

from conftest import load_script, run_script, write

lb = load_script("contributor-onboarding", "labels")


def test_default_set_is_valid_and_has_github_names():
    labels = lb.generate(lb.DEFAULT_PRESETS, [], False)
    assert lb.validate(labels) == []
    names = {label["name"] for label in labels}
    assert {"bug", "good first issue", "help wanted", "needs-triage", "dependencies"} <= names


def test_prefixed_keeps_github_contributor_labels():
    labels = lb.generate(["type", "contributor", "status"], [], True)
    names = {label["name"] for label in labels}
    assert "type: bug" in names and "status: needs triage" in names
    assert "good first issue" in names and "help wanted" in names
    assert lb.validate(labels) == []


def test_areas_are_added_and_normalised():
    labels = lb.generate(["type"], ["CLI", " docs ", ""], False)
    names = [label["name"] for label in labels]
    assert "area: cli" in names and "area: docs" in names
    assert len(names) == len(lb.PRESETS["type"]) + 2


def test_validate_catches_problems():
    bad = [
        {"name": "bug", "color": "#d73a4a"},
        {"name": "Bug", "color": "d73a4a"},
        {"name": "x" * 51, "color": "ffffff"},
        {"name": "ok", "color": "ffffff", "description": "d" * 101},
        {"color": "ffffff"},
        "nope",
    ]
    problems = "\n".join(lb.validate(bad))
    assert "6 hex digits" in problems
    assert "duplicate" in problems
    assert "longer than 50" in problems
    assert "longer than 100" in problems
    assert "missing name" in problems
    assert "must be an object" in problems
    assert lb.validate({"name": "x"}) != []


def test_commands_are_shell_safe():
    labels = [{"name": "good first issue", "color": "7057ff", "description": "It's easy; $(rm -rf /)"}]
    script = lb.commands(labels, "owner/repo")
    line = script.strip().splitlines()[-1]
    argv = shlex.split(line)
    assert argv[:4] == ["gh", "label", "create", "good first issue"]
    assert "It's easy; $(rm -rf /)" in argv
    assert argv[-3:] == ["--repo", "owner/repo", "--force"]


def test_cli_roundtrip(tmp_path):
    proc = run_script("contributor-onboarding", "labels", "generate", "--area", "api")
    assert proc.returncode == 0
    path = write(tmp_path, "labels.json", proc.stdout)
    assert run_script("contributor-onboarding", "labels", "validate", str(path)).returncode == 0
    out = run_script("contributor-onboarding", "labels", "commands", str(path), "--repo", "o/r")
    assert out.returncode == 0
    assert out.stdout.startswith("#!/bin/sh")
    assert out.stdout.count("gh label create") == len(json.loads(path.read_text()))


def test_cli_validate_failure_and_bad_repo(tmp_path):
    bad = write(tmp_path, "bad.json", json.dumps([{"name": "a", "color": "zzz"}]))
    proc = run_script("contributor-onboarding", "labels", "validate", str(bad), "--json")
    assert proc.returncode == 1
    assert json.loads(proc.stdout)["ok"] is False
    assert run_script("contributor-onboarding", "labels", "commands", str(bad)).returncode == 1
    good = write(tmp_path, "good.json", json.dumps([{"name": "a", "color": "ffffff"}]))
    assert run_script("contributor-onboarding", "labels", "commands", str(good), "--repo", "bad repo").returncode == 2
    assert run_script("contributor-onboarding", "labels", "validate", str(tmp_path / "missing.json")).returncode == 2
