import datetime as dt
import json

from conftest import load_script, run_script, write

tr = load_script("issue-triage", "triage_report")

NOW = dt.datetime(2026, 6, 1, tzinfo=dt.UTC)


def issue(number, title, labels=(), days_idle=1, body="", comments=0, **extra):
    updated = (NOW - dt.timedelta(days=days_idle)).isoformat().replace("+00:00", "Z")
    return {
        "number": number,
        "title": title,
        "body": body,
        "labels": [{"name": n} for n in labels],
        "createdAt": updated,
        "updatedAt": updated,
        "comments": comments,
        "url": f"https://github.com/o/r/issues/{number}",
        **extra,
    }


def build(issues, **kw):
    params = {"stale_days": 60, "info_days": 14, "dup_threshold": 0.85} | kw
    return tr.build(issues, NOW, params["stale_days"], params["info_days"], params["dup_threshold"])


def numbers(entries):
    return [e["number"] for e in entries]


def test_untriaged_detection():
    report = build(
        [
            issue(1, "Crash on start"),
            issue(2, "Add dark mode", ["enhancement"]),
            issue(3, "Something", ["needs-triage", "bug"]),
            issue(4, "Thing", ["type: question"]),
            issue(5, "Other", ["area: cli"]),
        ]
    )
    assert numbers(report["untriaged"]) == [1, 3]


def test_needs_info_overdue_sorted_by_idle():
    report = build(
        [
            issue(1, "a", ["needs-info"], days_idle=20),
            issue(2, "b", ["status: needs repro"], days_idle=40),
            issue(3, "c", ["needs-info"], days_idle=3),
        ]
    )
    assert numbers(report["needs_info_overdue"]) == [2, 1]


def test_missing_repro_only_for_bugs_without_details():
    report = build(
        [
            issue(1, "broken", ["bug"], body="it does not work"),
            issue(2, "broken too", ["bug"], body="Steps to reproduce:\n1. run\nExpected: ok"),
            issue(3, "idea", ["enhancement"], body="it does not work"),
        ]
    )
    assert numbers(report["missing_repro"]) == [1]


def test_stale_with_exemptions():
    report = build(
        [
            issue(1, "old", ["bug"], days_idle=100),
            issue(2, "old pinned", ["pinned"], days_idle=100),
            issue(3, "old security", ["security"], days_idle=100),
            issue(4, "fresh", ["bug"], days_idle=5),
        ]
    )
    assert numbers(report["stale"]) == [1]
    assert numbers(build([issue(1, "x", days_idle=30)], stale_days=20)["stale"]) == [1]


def test_duplicates_by_title_similarity():
    report = build(
        [
            issue(10, "Crash when config file is empty"),
            issue(11, "crash when the config file is empty!"),
            issue(12, "Add support for YAML output"),
        ]
    )
    assert report["possible_duplicates"] == [{"issues": [10, 11], "similarity": 1.0}]


def test_good_first_issue_candidates():
    report = build(
        [
            issue(1, "Fix typo in README", body="'teh' should be 'the'"),
            issue(2, "Docs: add FAQ", ["documentation"]),
            issue(3, "Typo", ["good first issue"]),
            issue(4, "Rewrite the parser", ["enhancement"], body="big"),
        ]
    )
    assert numbers(report["good_first_issue_candidates"]) == [1, 2]


def test_comment_formats_and_pull_requests_skipped():
    assert tr.comment_count({"comments": [{"body": "a"}, {"body": "b"}]}) == 2
    assert tr.comment_count({"comments": {"totalCount": 4}}) == 4
    assert tr.comment_count({}) == 0
    report = build([issue(1, "pr", pullRequest={"url": "x"})])
    assert report["untriaged"] == []


def test_markdown_format():
    text = tr.format_report(build([issue(1, "Crash on start"), issue(2, "old", ["bug"], days_idle=90)]), True)
    assert text.startswith("# Triage report: 2 open issue(s)")
    assert "## Untriaged (1)" in text and "- #1 Crash on start" in text
    assert "idle 90d" in text


def test_cli(tmp_path):
    data = [issue(1, "Crash"), issue(2, "Docs", ["documentation"])]
    f = write(tmp_path, "issues.json", json.dumps(data))
    proc = run_script("issue-triage", "triage_report", str(f), "--json", "--now", NOW.isoformat())
    assert proc.returncode == 0
    assert numbers(json.loads(proc.stdout)["untriaged"]) == [1]
    proc = run_script("issue-triage", "triage_report", "-", "--fail-on-untriaged", stdin=json.dumps(data))
    assert proc.returncode == 1
    assert run_script("issue-triage", "triage_report", "-", stdin='{"not": "a list"}').returncode == 2
    assert run_script("issue-triage", "triage_report", str(tmp_path / "missing.json")).returncode == 2
