import json

import pytest

from conftest import load_script, run_script, write

gs = load_script("security-policy", "gen_security")
yaml = pytest.importorskip("yaml")


def polyglot(root):
    write(root, ".github/workflows/ci.yml", "name: CI\n")
    write(root, "pyproject.toml", "[project]\nname='x'\n")
    write(root, "requirements.txt", "requests\n")
    write(root, "web/package.json", "{}")
    write(root, "Dockerfile", "FROM python:3.13\n")
    write(root, "node_modules/dep/package.json", "{}")
    write(root, "vendor/x/composer.json", "{}")


def test_detect_ecosystems(tmp_path):
    polyglot(tmp_path)
    found = gs.detect_ecosystems(tmp_path)
    assert found == [
        {"ecosystem": "github-actions", "directory": "/"},
        {"ecosystem": "pip", "directory": "/"},
        {"ecosystem": "npm", "directory": "/web"},
        {"ecosystem": "docker", "directory": "/"},
    ]


def test_dependabot_yaml_is_valid(tmp_path):
    polyglot(tmp_path)
    text = gs.dependabot_yaml(gs.detect_ecosystems(tmp_path), "weekly", True, 5)
    data = yaml.safe_load(text)
    assert data["version"] == 2
    ecos = [(u["package-ecosystem"], u["directory"]) for u in data["updates"]]
    assert ("npm", "/web") in ecos and ("github-actions", "/") in ecos
    actions = next(u for u in data["updates"] if u["package-ecosystem"] == "github-actions")
    assert actions["commit-message"]["prefix"] == "ci"
    assert actions["groups"]["github-actions-minor-and-patch"]["update-types"] == ["minor", "patch"]
    assert all(u["schedule"]["interval"] == "weekly" for u in data["updates"])
    plain = yaml.safe_load(gs.dependabot_yaml([{"ecosystem": "pip", "directory": "/"}], "monthly", False, 2))
    assert "groups" not in plain["updates"][0] and plain["updates"][0]["open-pull-requests-limit"] == 2


def test_security_md_content():
    text = gs.security_md("demo", "o/demo", ["2.x", "1.9.x"], 3, 60)
    assert "https://github.com/o/demo/security/advisories/new" in text
    assert "| 2.x | :white_check_mark: |" in text and "| 1.9.x |" in text
    assert "3 working days" in text and "6 working days" in text and "60 days" in text
    assert "@" not in text.replace("advisories", "")


def test_check_reports_missing_and_partial_coverage(tmp_path):
    polyglot(tmp_path)
    result = gs.check(tmp_path)
    assert not result["ok"]
    assert any("SECURITY.md" in p for p in result["problems"])
    assert any("dependabot.yml" in p for p in result["problems"])
    write(tmp_path, "SECURITY.md", gs.security_md("x", "o/x", ["1.x"], 5, 90))
    write(tmp_path, ".github/dependabot.yml", "version: 2\nupdates:\n  - package-ecosystem: pip\n    directory: /\n")
    result = gs.check(tmp_path)
    missing = [p for p in result["problems"] if "does not cover" in p]
    assert len(missing) == 3 and any("'npm'" in p for p in missing)


def test_check_passes_when_complete(tmp_path):
    polyglot(tmp_path)
    write(tmp_path, ".github/SECURITY.md", gs.security_md("x", "o/x", ["1.x"], 5, 90))
    write(tmp_path, ".github/dependabot.yml", gs.dependabot_yaml(gs.detect_ecosystems(tmp_path), "weekly", True, 5))
    assert gs.check(tmp_path)["ok"]


def test_check_security_md_without_channel_and_renovate(tmp_path):
    write(tmp_path, "SECURITY.md", "# Security\n\nBe careful.\n")
    write(tmp_path, "renovate.json", "{}")
    result = gs.check(tmp_path)
    assert any("private reporting channel" in p for p in result["problems"])
    assert not any("dependabot" in p for p in result["problems"])
    assert any("Renovate" in n for n in result["notes"])


def test_cli_write_never_overwrites(tmp_path):
    write(tmp_path, "requirements.txt", "x\n")
    args = ["dependabot", str(tmp_path), "--write"]
    assert run_script("security-policy", "gen_security", *args).returncode == 0
    assert (tmp_path / ".github/dependabot.yml").exists()
    assert run_script("security-policy", "gen_security", *args).returncode == 1
    assert run_script("security-policy", "gen_security", *args, "--force").returncode == 0
    md = ["security-md", str(tmp_path), "--repo", "o/r", "--write"]
    assert run_script("security-policy", "gen_security", *md).returncode == 0
    assert run_script("security-policy", "gen_security", *md).returncode == 1


def test_cli_check_json_and_errors(tmp_path):
    proc = run_script("security-policy", "gen_security", "check", str(tmp_path), "--json")
    assert proc.returncode == 1 and json.loads(proc.stdout)["ok"] is False
    assert run_script("security-policy", "gen_security", "dependabot", str(tmp_path)).returncode == 1
    bad_repo = run_script("security-policy", "gen_security", "security-md", "--repo", "not a repo")
    assert bad_repo.returncode == 2
    assert run_script("security-policy", "gen_security", "ecosystems", str(tmp_path / "nope")).returncode == 2
