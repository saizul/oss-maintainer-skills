import json

from conftest import git, load_script, requires_git, run_script, write

rp = load_script("release-checklist", "release_preflight")

CHANGELOG = """# Changelog

## [Unreleased]

## [1.4.0] - 2026-05-01

### Added

- Search command.

## [1.3.0] - 2026-01-01

- Older.
"""


def project(root, version="1.4.0", changelog=CHANGELOG):
    write(root, "pyproject.toml", f'[project]\nname = "demo"\nversion = "{version}"\n')
    write(root, "package.json", json.dumps({"name": "demo", "version": version}))
    write(root, "CHANGELOG.md", changelog)
    write(root, "LICENSE", "MIT\n")


def statuses(result):
    return {c["id"]: c["status"] for c in result["checks"]}


def test_ready_without_git(tmp_path):
    project(tmp_path)
    result = rp.run(tmp_path, None, [], False, "v", ["main"])
    assert result["version"] == "1.4.0" and result["tag"] == "v1.4.0"
    assert result["ready"], result
    assert statuses(result) == {"semver": "pass", "manifests": "pass", "changelog": "pass"}


def test_version_mismatch(tmp_path):
    project(tmp_path)
    write(tmp_path, "package.json", json.dumps({"version": "1.3.9"}))
    result = rp.run(tmp_path, "1.4.0", [], False, "v", ["main"])
    assert statuses(result)["manifests"] == "fail"
    assert "package.json=1.3.9" in result["checks"][1]["message"]
    auto = rp.run(tmp_path, None, [], False, "v", ["main"])
    assert not auto["ready"] and auto["checks"][0]["id"] == "version"


def test_version_files_poetry_and_cargo(tmp_path):
    write(tmp_path, "pyproject.toml", '[tool.poetry]\nname = "x"\nversion = "2.0.0"\n')
    write(tmp_path, "Cargo.toml", '[package]\nname = "x"\nversion = "2.0.0"\n')
    write(tmp_path, "src/x/_version.py", '__version__ = "2.0.1"\n')
    found = rp.manifest_versions(tmp_path, ["src/x/_version.py", "missing.py"])
    assert found == {
        "pyproject.toml": "2.0.0",
        "Cargo.toml": "2.0.0",
        "src/x/_version.py": "2.0.1",
        "missing.py": "<missing file>",
    }


def test_changelog_states(tmp_path):
    project(tmp_path)
    assert rp.changelog_check(tmp_path, "1.4.0")[0] == "pass"
    assert rp.changelog_check(tmp_path, "1.3.0")[0] == "pass"
    status, msg = rp.changelog_check(tmp_path, "1.5.0")
    assert status == "fail" and "Unreleased" in msg
    write(tmp_path, "CHANGELOG.md", "# Changelog\n\n## [1.5.0] - 2026-06-01\n\n## [1.4.0]\n\n- x\n")
    status, msg = rp.changelog_check(tmp_path, "1.5.0")
    assert status == "fail" and "no entries" in msg
    (tmp_path / "CHANGELOG.md").unlink()
    assert rp.changelog_check(tmp_path, "1.5.0")[0] == "fail"


def test_prerelease_heading_does_not_match_final(tmp_path):
    project(tmp_path, changelog="# Changelog\n\n## [2.0.0-rc.1] - 2026-01-01\n\n- x\n")
    assert rp.changelog_check(tmp_path, "2.0.0")[0] == "fail"
    assert rp.changelog_check(tmp_path, "2.0.0-rc.1")[0] == "pass"


def test_invalid_semver_and_missing_license(tmp_path):
    project(tmp_path)
    (tmp_path / "LICENSE").unlink()
    result = rp.run(tmp_path, "1.4", [], False, "v", ["main"])
    s = statuses(result)
    assert s["semver"] == "fail" and s["license"] == "fail"


@requires_git
def test_git_checks(tmp_path):
    project(tmp_path)
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "chore: release 1.4.0")
    result = rp.run(tmp_path, None, [], True, "v", ["main"])
    s = statuses(result)
    assert s["clean-tree"] == "pass" and s["tag-free"] == "pass" and s["branch"] == "pass"
    assert result["ready"]
    git(tmp_path, "tag", "v1.4.0")
    write(tmp_path, "new.txt", "dirty")
    result = rp.run(tmp_path, None, [], True, "v", ["release"])
    s = statuses(result)
    assert s["clean-tree"] == "fail" and s["tag-free"] == "fail" and s["branch"] == "warn"
    assert not result["ready"]


def test_not_a_git_repo_is_a_warning(tmp_path):
    project(tmp_path)
    result = rp.run(tmp_path, None, [], True, "v", ["main"])
    if "git" in statuses(result):
        assert statuses(result)["git"] == "warn"
    assert result["ready"]


def test_cli(tmp_path):
    project(tmp_path)
    proc = run_script("release-checklist", "release_preflight", str(tmp_path), "--no-git", "--json")
    assert proc.returncode == 0 and json.loads(proc.stdout)["ready"] is True
    proc = run_script("release-checklist", "release_preflight", str(tmp_path), "--no-git", "--version", "9.9.9")
    assert proc.returncode == 1 and "Not ready" in proc.stdout
    assert run_script("release-checklist", "release_preflight", str(tmp_path / "x")).returncode == 2
