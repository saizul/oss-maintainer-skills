import json

import pytest

from conftest import load_script, run_script, write

ld = load_script("project-launch", "launch_drafts")


def levels(issues):
    return [i["level"] for i in issues]


def test_good_hn_title_passes():
    assert ld.lint_title("Show HN: dbsnap – Consistent Postgres snapshots to S3", "hn") == []


@pytest.mark.parametrize(
    ("title", "needle"),
    [
        ("dbsnap – snapshots", "Show HN"),
        ("Show HN: " + "x" * 80, "characters"),
        ("Show HN: dbsnap is here!", "exclamation"),
        ("Show HN: dbsnap 🚀 snapshots", "emoji"),
        ("Show HN: dbsnap, please upvote", "upvotes"),
    ],
)
def test_hn_title_errors(title, needle):
    issues = ld.lint_title(title, "hn")
    assert "error" in levels(issues)
    assert any(needle.lower() in i["message"].lower() for i in issues)


def test_hype_and_shouting_are_warnings():
    issues = ld.lint_title("Show HN: The BEST and FASTEST JSON tool", "hn")
    assert levels(issues) == ["warning", "warning"]
    # JSON is an allowed acronym; 'best' only matches as a whole word
    assert ld.lint_title("Show HN: bestiary – JSON tools for D&D", "hn") == []


def test_reddit_limits():
    assert ld.lint_title("I built x" * 10, "reddit") == []
    assert "error" in levels(ld.lint_title("x" * 301, "reddit"))
    assert levels(ld.lint_title("I built x 🚀", "reddit")) == ["warning"]


def test_pitch_from_readme(tmp_path):
    readme = write(
        tmp_path,
        "README.md",
        "# dbsnap\n\n[![CI](https://x/badge.svg)](https://x)\n\n"
        "**dbsnap** is a CLI that snapshots [Postgres](https://postgresql.org) to S3.\nIt is fast.\n\n## Install\n",
    )
    assert ld.pitch_from_readme(readme) == "dbsnap is a CLI that snapshots Postgres to S3. It is fast."


def test_hn_title_generation_and_truncation():
    t, cut = ld.hn_title("dbsnap", "dbsnap is a CLI that snapshots databases. More text.")
    assert (t, cut) == ("Show HN: dbsnap – A CLI that snapshots databases", False)
    long, cut = ld.hn_title("tool", "A " + "very long description " * 10)
    assert cut and len(long) <= ld.HN_MAX and long.startswith("Show HN: tool – ")
    pitch = "Snapshots Postgres and MySQL databases to S3, with retention policies and encryption at rest"
    clause, cut = ld.hn_title("tool", pitch)
    assert cut and clause == "Show HN: tool – Snapshots Postgres and MySQL databases to S3"


def test_shortened_title_gets_a_warning_and_case_is_kept():
    d = ld.drafts("tool", "https://e.com", "Agent Skills " + "for very long things " * 10, None, [])
    assert any("cut" in i["message"] for i in d["show_hn"]["title_lint"])
    assert d["reddit"]["title"].startswith("I built tool, Agent Skills")


def test_drafts_structure():
    d = ld.drafts(
        "dbsnap",
        "https://github.com/o/dbsnap",
        "A CLI that snapshots databases.",
        None,
        ["Python", "CLI", "dev-ops", "a", "b"],
    )
    assert d["show_hn"]["title_lint"] == []
    assert "[FILL IN" in d["show_hn"]["first_comment"]
    assert d["reddit"]["title"] == "I built dbsnap, a CLI that snapshots databases"
    assert d["devto"]["tags"] == ["python", "cli", "devops", "a"]
    assert "published: false" in d["devto"]["markdown"]
    assert d["social"]["length"] <= ld.SOCIAL_MAX


def test_social_post_truncates():
    d = ld.drafts("x", "https://example.com/" + "p" * 50, "word " * 100, None, [])
    assert d["social"]["length"] <= ld.SOCIAL_MAX
    assert d["social"]["text"].endswith("https://example.com/" + "p" * 50)


def test_cli(tmp_path):
    proc = run_script("project-launch", "launch_drafts", "lint-title", "Show HN: x – a thing", "--json")
    assert proc.returncode == 0 and json.loads(proc.stdout)["issues"] == []
    assert run_script("project-launch", "launch_drafts", "lint-title", "bad title!").returncode == 1
    readme = write(tmp_path, "README.md", "# demo\n\nDemo converts CSV to JSON.\n")
    proc = run_script(
        "project-launch", "launch_drafts", "drafts", "--name", "demo", "--url", "https://e.com", "--readme", str(readme)
    )
    assert (
        proc.returncode == 0
        and "=== Show HN ===" in proc.stdout
        and "Show HN: demo – Demo converts CSV to JSON" in proc.stdout
    )
    empty = write(tmp_path, "EMPTY.md", "# demo\n")
    args = ["drafts", "--name", "d", "--url", "https://e.com", "--readme", str(empty)]
    assert run_script("project-launch", "launch_drafts", *args).returncode == 2
