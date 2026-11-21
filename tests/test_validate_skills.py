import importlib.util
import json
import shutil
import subprocess
import sys

import pytest

from conftest import REPO, write

spec = importlib.util.spec_from_file_location("validate_skills", REPO / "tools" / "validate_skills.py")
vs = importlib.util.module_from_spec(spec)
sys.modules["validate_skills"] = vs
spec.loader.exec_module(vs)

SKILL = """---
name: demo-skill
description: Does a demo thing. Use when the user asks for a demo.
license: MIT
metadata:
  author: Someone
  version: "0.1.0"
---

# Demo

## When to use

- demo

## When not to use

- never

## Workflow

1. Read [the guide](references/guide.md).
2. Run `scripts/demo.py`.

## Output

- a demo
"""


def make_repo(root, skill=SKILL, name="demo-skill"):
    d = root / "skills" / name
    write(d, "SKILL.md", skill)
    write(d, "references/guide.md", "# Guide\n")
    write(d, "scripts/demo.py", "import argparse\nargparse.ArgumentParser(description='demo').parse_args()\n")
    write(root, "tests/test_demo.py", "")
    write(root, "templates/skill/SKILL.md", SKILL)
    write(root, ".claude-plugin/plugin.json", json.dumps({"name": "demo", "version": "0.1.0"}))
    market = {
        "name": "demo",
        "owner": {"name": "Someone"},
        "plugins": [{"name": "demo", "source": "./", "skills": [f"./skills/{name}"]}],
    }
    write(root, ".claude-plugin/marketplace.json", json.dumps(market))
    return d


def test_this_repository_is_valid():
    result = vs.validate_repo(REPO)
    assert result["errors"] == []
    assert len(result["skills"]) >= 6


def test_minimal_repo_is_valid(tmp_path):
    make_repo(tmp_path)
    assert vs.validate_repo(tmp_path)["errors"] == []


@pytest.mark.parametrize(
    ("old", "new", "needle"),
    [
        ("name: demo-skill", "name: Demo_Skill", "lowercase"),
        ("name: demo-skill", "name: other-skill", "match the folder"),
        ("name: demo-skill", "name: demo--skill", "lowercase"),
        ("Use when the user asks for a demo.", "Helps.", "Use when"),
        ("license: MIT", "license: MIT\nauthor: me", "unknown frontmatter"),
        ("## When not to use", "## Notes", "When not to use"),
        ("references/guide.md", "references/missing.md", "does not exist"),
        ("`scripts/demo.py`", "`scripts/gone.py`", "does not exist"),
    ],
)
def test_skill_errors(tmp_path, old, new, needle):
    d = make_repo(tmp_path)
    (d / "SKILL.md").write_text(SKILL.replace(old, new), encoding="utf-8")
    errors = vs.validate_skill(d, tmp_path)
    assert any(needle in e for e in errors), errors


def test_long_description_and_name(tmp_path):
    d = make_repo(tmp_path)
    (d / "SKILL.md").write_text(SKILL.replace("Does a demo thing.", "x" * 1100), encoding="utf-8")
    assert any("max 1024" in e for e in vs.validate_skill(d, tmp_path))
    long_name = "a" * 65
    d2 = make_repo(tmp_path, SKILL.replace("demo-skill", long_name), long_name)
    assert any("max 64" in e for e in vs.validate_skill(d2, tmp_path))


def test_body_line_limit(tmp_path):
    d = make_repo(tmp_path)
    (d / "SKILL.md").write_text(SKILL + "line\n" * 401, encoding="utf-8")
    assert any("max 400" in e for e in vs.validate_skill(d, tmp_path))


def test_script_needs_test_and_help(tmp_path):
    d = make_repo(tmp_path)
    (tmp_path / "tests" / "test_demo.py").unlink()
    write(d, "scripts/broken.py", "raise SystemExit(3)\n")
    errors = vs.validate_skill(d, tmp_path)
    assert any("tests/test_demo.py" in e for e in errors)
    assert any("broken.py --help" in e for e in errors)
    assert not any("--help" in e for e in vs.validate_skill(d, tmp_path, run_help=False))


def test_frontmatter_parse_errors(tmp_path):
    with pytest.raises(vs.FrontmatterError):
        vs.parse_frontmatter("no frontmatter")
    with pytest.raises(vs.FrontmatterError):
        vs.parse_frontmatter("---\nname: x\n")
    with pytest.raises(vs.FrontmatterError):
        vs.parse_frontmatter("---\nname: x\nname: y\n---\n")
    with pytest.raises(vs.FrontmatterError):
        vs.parse_frontmatter("---\ntags: [a, b]\n---\n")
    with pytest.raises(vs.FrontmatterError, match="quotes"):
        vs.parse_frontmatter("---\ndescription: Does X. Use when: always\n---\n")
    meta, body, _ = vs.parse_frontmatter("---\nname: 'it''s'\ndescription: \"a: b\"\n---\nbody")
    assert meta == {"name": "it's", "description": "a: b"} and body == "body"


def test_paths_in_code_blocks_must_exist_but_headings_there_do_not_count(tmp_path):
    d = make_repo(tmp_path)
    text = SKILL.replace("## Output\n\n- a demo\n", "```\n## Output\npython3 scripts/nope.py\n```\n")
    (d / "SKILL.md").write_text(text, encoding="utf-8")
    errors = vs.validate_skill(d, tmp_path)
    assert any("'## Output'" in e for e in errors)
    assert any("scripts/nope.py" in e for e in errors)


def test_marketplace_must_list_every_skill(tmp_path):
    make_repo(tmp_path)
    second = tmp_path / "skills" / "second-skill"
    shutil.copytree(tmp_path / "skills" / "demo-skill", second)
    (second / "SKILL.md").write_text(SKILL.replace("demo-skill", "second-skill"), encoding="utf-8")
    errors = vs.validate_repo(tmp_path)["errors"]
    assert any("not listed" in e and "second-skill" in e for e in errors)


def test_marketplace_field_errors(tmp_path):
    make_repo(tmp_path)
    bad = {
        "name": "bad name",
        "plugins": [{"name": "other", "source": "../x", "skills": ["skills/demo-skill", "./skills/ghost"]}],
    }
    write(tmp_path, ".claude-plugin/marketplace.json", json.dumps(bad))
    errors = "\n".join(vs.validate_manifests(tmp_path, ["demo-skill"]))
    assert "'name' is required" in errors
    assert "owner.name" in errors
    assert "must start with './'" in errors
    assert "ghost" in errors
    write(tmp_path, ".claude-plugin/marketplace.json", "{not json")
    assert any("invalid JSON" in e for e in vs.validate_manifests(tmp_path, []))


def test_plugin_name_must_match_root_entry(tmp_path):
    make_repo(tmp_path)
    write(tmp_path, ".claude-plugin/plugin.json", json.dumps({"name": "different", "version": "1"}))
    assert any("differs from plugin.json" in e for e in vs.validate_manifests(tmp_path, ["demo-skill"]))


def test_cli(tmp_path):
    make_repo(tmp_path)
    tool = REPO / "tools" / "validate_skills.py"
    ok = subprocess.run([sys.executable, str(tool), str(tmp_path), "--json"], capture_output=True, text=True)
    assert ok.returncode == 0 and json.loads(ok.stdout)["ok"] is True
    (tmp_path / "templates" / "skill" / "SKILL.md").unlink()
    bad = subprocess.run([sys.executable, str(tool), str(tmp_path)], capture_output=True, text=True)
    assert bad.returncode == 1 and "templates/skill/SKILL.md" in bad.stdout
    missing = subprocess.run([sys.executable, str(tool), str(tmp_path / "nope")], capture_output=True, text=True)
    assert missing.returncode == 2
