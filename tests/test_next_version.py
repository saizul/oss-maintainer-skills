import json

import pytest

from conftest import git, load_script, requires_git, run_script, write

nv = load_script("conventional-commits-release", "next_version")


def commits(*subjects):
    return [nv.parse_commit("", s) for s in subjects]


def test_parse_header_scope_and_bang():
    c = nv.parse_commit("abc", "feat(cli)!: drop --old flag")
    assert (c.type, c.scope, c.subject, c.breaking, c.conventional) == ("feat", "cli", "drop --old flag", True, True)
    plain = nv.parse_commit("", "Update README")
    assert plain.type == "other" and not plain.conventional


def test_breaking_footer():
    c = nv.parse_commit(
        "abc", "refactor: rename option", "Body.\n\nBREAKING CHANGE: `timeout` is now `timeout_seconds`"
    )
    assert c.breaking and "timeout_seconds" in c.breaking_note
    assert nv.parse_commit("", "fix: x", "BREAKING-CHANGE: y").breaking


@pytest.mark.parametrize(
    ("subjects", "bump"),
    [
        (["docs: typo", "chore: deps"], "none"),
        (["fix: a", "docs: b"], "patch"),
        (["perf: faster"], "patch"),
        (["fix: a", "feat: b"], "minor"),
        (["feat: a", "fix!: b"], "major"),
    ],
)
def test_bump_for(subjects, bump):
    assert nv.bump_for(commits(*subjects)) == bump


@pytest.mark.parametrize(
    ("current", "bump", "pre", "zero", "expected"),
    [
        ("1.2.3", "patch", None, True, "1.2.4"),
        ("1.2.3", "minor", None, True, "1.3.0"),
        ("1.2.3", "major", None, True, "2.0.0"),
        ("v1.2.3", "none", None, True, "1.2.3"),
        ("0.4.1", "major", None, True, "0.5.0"),
        ("0.4.1", "major", None, False, "1.0.0"),
        ("0.0.0", "minor", None, True, "0.1.0"),
        ("1.2.3", "minor", "rc", True, "1.3.0-rc.1"),
    ],
)
def test_next_version(current, bump, pre, zero, expected):
    assert nv.next_version(current, bump, pre, zero) == expected


def test_prerelease_continue_and_finish():
    assert nv.next_version("1.3.0-rc.1", "patch", "rc") == "1.3.0-rc.2"
    assert nv.next_version("1.3.0-rc.2", "minor") == "1.3.0"
    assert nv.next_version("2.0.0-beta.3", "major") == "2.0.0"
    assert nv.next_version("1.3.0-rc.1", "minor", "beta") == "1.3.0-beta.1"
    # rc of a minor line cannot absorb a major bump
    assert nv.next_version("1.3.0-rc.1", "major") == "2.0.0"


def test_invalid_version():
    with pytest.raises(ValueError):
        nv.parse_version("1.2")


def test_changelog_groups_and_links():
    cs = [
        nv.parse_commit("a" * 40, "feat(api): add search"),
        nv.parse_commit("b" * 40, "fix: handle empty input"),
        nv.parse_commit("c" * 40, "feat!: remove v1 endpoints"),
        nv.parse_commit("d" * 40, "docs: update"),
        nv.parse_commit("e" * 40, "chore: bump deps"),
    ]
    text = nv.changelog("2.0.0", cs, "2026-01-02", "https://github.com/o/r", set())
    assert text.startswith("## [2.0.0] - 2026-01-02")
    assert "### Breaking changes" in text and "### Features" in text and "### Bug fixes" in text
    assert "**api:** add search ([aaaaaaa](https://github.com/o/r/commit/" in text
    assert "### Documentation" not in text and "bump deps" not in text
    full = nv.changelog("2.0.0", cs, "2026-01-02", None, {"docs", "other"})
    assert "### Documentation" in full and "bump deps (eeeeeee)" in full


def test_parse_log_record_format_and_skips():
    raw = "h1\x1ffeat: one\x1f\x1e\nh2\x1fchore(release): 1.0.0\x1f\x1e\nh3\x1fMerge branch 'x'\x1f\x1e"
    parsed = [c for c in nv.parse_log(raw) if not nv.is_skipped(c)]
    assert [c.hash for c in parsed] == ["h1"]


def test_cli_stdin_json():
    proc = run_script(
        "conventional-commits-release",
        "next_version",
        "--current",
        "1.4.2",
        "--json",
        "--date",
        "2026-05-01",
        stdin="feat: new thing\nfix: bug\nrandom commit\n",
    )
    assert proc.returncode == 0
    data = json.loads(proc.stdout)
    assert (data["bump"], data["next"], data["tag"]) == ("minor", "1.5.0", "v1.5.0")
    assert data["non_conventional"] == ["random commit"]


def test_cli_fail_if_none_and_bad_version(tmp_path):
    f = write(tmp_path, "c.txt", "docs: only docs\n")
    proc = run_script("conventional-commits-release", "next_version", "--input", str(f), "--fail-if-none")
    assert proc.returncode == 1 and "nothing to release" in proc.stdout
    bad = run_script("conventional-commits-release", "next_version", "--input", str(f), "--current", "one")
    assert bad.returncode == 2


@requires_git
def test_cli_git_since_latest_tag(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    write(tmp_path, "a.txt", "1")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "feat: initial")
    git(tmp_path, "tag", "v1.0.0")
    write(tmp_path, "a.txt", "2")
    git(tmp_path, "commit", "-q", "-am", "fix(core): off by one")
    proc = run_script("conventional-commits-release", "next_version", "--git", "--repo-dir", str(tmp_path), "--json")
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert (data["current"], data["bump"], data["next"], data["commits"]) == ("1.0.0", "patch", "1.0.1", 1)
    assert "**core:** off by one" in data["changelog"]


def test_cli_git_outside_repo(tmp_path):
    proc = run_script("conventional-commits-release", "next_version", "--git", "--repo-dir", str(tmp_path))
    assert proc.returncode == 2


def test_git_revert_commit_is_a_revert():
    c = nv.parse_commit("abc", 'Revert "feat(api): add bulk export"', "This reverts commit 1234567.")
    assert (c.type, c.subject, c.conventional, c.breaking) == ("revert", "feat(api): add bulk export", True, False)
    assert nv.bump_for([c]) == "patch"
    notes = nv.changelog("1.2.1", [c], "2026-11-27", None, set())
    assert "### Reverts\n\n- feat(api): add bulk export (abc)" in notes
    assert "Other changes" not in notes


def test_revert_lookalikes_are_not_git_reverts():
    assert nv.parse_commit("", "Revert the cache change").type == "other"
    assert nv.parse_commit("", 'revert: "feat: x"').type == "revert"


def test_pr_references_link_with_repo_url():
    cs = [nv.parse_commit("a" * 40, "feat: add --only flag (#12)"), nv.parse_commit("", "fix: retry on 503 (#7) (#9)")]
    url = "https://github.com/OWNER/NAME/"
    notes = nv.changelog("1.3.0", cs, "2026-11-27", url, set())
    assert "- add --only flag ([#12](https://github.com/OWNER/NAME/pull/12)) ([aaaaaaa](" in notes
    assert (
        "retry on 503 ([#7](https://github.com/OWNER/NAME/pull/7)) ([#9](https://github.com/OWNER/NAME/pull/9))"
        in notes
    )
    plain = nv.changelog("1.3.0", cs, "2026-11-27", None, set())
    assert "- add --only flag (#12) (aaaaaaa)" in plain


def test_cli_revert_and_links(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text('Revert "feat: dark mode"\nfix: crash on start (#4)\n', encoding="utf-8")
    out = run_script(
        "conventional-commits-release",
        "next_version",
        "--input",
        str(log),
        "--current",
        "1.0.0",
        "--repo-url",
        "https://github.com/o/r",
        "--json",
    )
    data = json.loads(out.stdout)
    assert data["next"] == "1.0.1" and data["non_conventional"] == []
    assert "[#4](https://github.com/o/r/pull/4)" in data["changelog"] and "- feat: dark mode" in data["changelog"]
