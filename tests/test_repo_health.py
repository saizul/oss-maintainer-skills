import json

from conftest import load_script, run_script, write

rh = load_script("repo-health-check", "repo_health")

GOOD_README = (
    "# demo\n\n"
    "[![CI](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)](x) "
    "[![License](https://img.shields.io/github/license/o/r)](LICENSE)\n\n"
    + ("Demo is a tool that does useful things for people. " * 20)
    + "\n\n## Installation\n\n```bash\npip install demo\n```\n\n## Usage\n\nRun it.\n\n"
    "## Contributing\n\nSee CONTRIBUTING.md.\n\n## License\n\nMIT\n"
)


def make_healthy(root):
    write(root, "README.md", GOOD_README)
    write(root, "LICENSE", "MIT License\n\n" + "Permission is hereby granted, free of charge. " * 10)
    write(root, "CONTRIBUTING.md", "How to contribute\n")
    write(root, ".github/CODE_OF_CONDUCT.md", "Be nice\n")
    write(root, "SECURITY.md", "Report privately\n")
    write(root, ".github/ISSUE_TEMPLATE/bug_report.yml", "name: Bug\n")
    write(root, ".github/ISSUE_TEMPLATE/feature_request.yml", "name: Feature\n")
    write(root, ".github/pull_request_template.md", "## What\n")
    write(root, ".github/workflows/ci.yml", "name: CI\n")
    write(root, ".github/dependabot.yml", "version: 2\n")
    write(root, "tests/test_demo.py", "def test_x():\n    pass\n")
    write(root, "CHANGELOG.md", "# Changelog\n")
    write(root, ".gitignore", "__pycache__/\n")


def test_empty_repo_scores_zero_with_fixes(tmp_path):
    report = rh.build_report(tmp_path, set())
    assert report["score"] == 0
    assert report["grade"] == "F"
    ids = {f["id"] for f in report["fixes"]}
    assert {"readme", "license", "ci", "tests", "security"} <= ids
    # Biggest gains first.
    gains = [f["points_available"] for f in report["fixes"]]
    assert gains == sorted(gains, reverse=True)


def test_healthy_repo_scores_100(tmp_path):
    make_healthy(tmp_path)
    report = rh.build_report(tmp_path, set())
    failed = [c["id"] for c in report["checks"] if not c["passed"]]
    assert failed == []
    assert report["score"] == 100
    assert report["grade"] == "A"


def test_partial_readme_sections(tmp_path):
    write(tmp_path, "README.md", "# demo\n\nShort.\n\n## Usage\n\nno code here\n")
    readme, sections, badges, _ = rh.check_readme(tmp_path)
    assert readme.points == 5
    assert sections.points == 4
    assert "Installation" in sections.fix
    assert badges.points == 0


def test_headings_inside_code_blocks_are_ignored():
    hs = rh.headings("# T\n\n```\n# not a heading\n```\n## Install\n")
    assert hs == ["t", "install"]


def test_truncated_license_gets_partial_credit(tmp_path):
    write(tmp_path, "LICENSE", "MIT\n")
    c = rh.check_license(tmp_path)
    assert c.points == 5 and "truncated" in c.fix


def test_community_files_found_in_docs_and_github(tmp_path):
    write(tmp_path, "docs/CONTRIBUTING.md", "x\n")
    write(tmp_path, ".github/SECURITY.md", "x\n")
    report = rh.build_report(tmp_path, set())
    by_id = {c["id"]: c for c in report["checks"]}
    assert by_id["contributing"]["passed"]
    assert by_id["security"]["passed"]


def test_test_files_detected_without_tests_dir(tmp_path):
    write(tmp_path, "src/app.test.ts", "x\n")
    assert rh.check_tests(tmp_path).passed
    write(tmp_path / "go", "pkg/thing_test.go", "x\n")
    assert rh.check_tests(tmp_path / "go").passed


def test_skip_excludes_checks_from_score(tmp_path):
    make_healthy(tmp_path)
    (tmp_path / "CHANGELOG.md").unlink()
    assert rh.build_report(tmp_path, set())["score"] < 100
    assert rh.build_report(tmp_path, {"changelog"})["score"] == 100


def test_cli_json_and_min_score_exit_code(tmp_path):
    make_healthy(tmp_path)
    proc = run_script("repo-health-check", "repo_health", str(tmp_path), "--json")
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert data["score"] == 100
    empty = tmp_path / "empty"
    empty.mkdir()
    proc = run_script("repo-health-check", "repo_health", str(empty), "--min-score", "50")
    assert proc.returncode == 1
    assert "Fixes, biggest gain first" in proc.stdout


def test_cli_missing_path_is_usage_error(tmp_path):
    proc = run_script("repo-health-check", "repo_health", str(tmp_path / "nope"))
    assert proc.returncode == 2
