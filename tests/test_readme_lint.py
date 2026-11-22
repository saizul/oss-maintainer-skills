import json

from conftest import load_script, run_script, write

rl = load_script("readme-writer", "readme_lint")

GOOD = """# demo

[![CI](https://github.com/o/r/actions/workflows/ci.yml/badge.svg)](https://github.com/o/r/actions)

demo is a command-line tool that turns messy CSV files into clean JSON for data teams.

## Installation

```bash
pip install demo
```

## Quick start

```bash
demo convert data.csv
```

## FAQ

**Why?** Because.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
"""


def rules(findings, severity=None):
    return {f.rule for f in findings if severity is None or f.severity == severity}


def test_good_readme_has_no_findings(tmp_path):
    write(tmp_path, "CONTRIBUTING.md")
    write(tmp_path, "LICENSE")
    assert rl.lint(GOOD, tmp_path) == []


def test_empty_readme():
    assert rules(rl.lint("")) == {"empty"}


def test_missing_everything():
    found = rules(rl.lint("Some text without structure.\n"), "error")
    assert {"title", "install", "quickstart", "code"} <= found


def test_pitch_ignores_badges_and_detects_missing():
    text = "# demo\n\n[![CI](https://img.shields.io/x)](y)\n\n## Install\n\n```\npip install demo\n```\n"
    assert "pitch" in rules(rl.lint(text), "error")


def test_long_pitch_warns():
    text = GOOD.replace(
        "demo is a command-line tool that turns messy CSV files into clean JSON for data teams.",
        "demo " + "really " * 60 + "works.",
    )
    assert "pitch" in rules(rl.lint(text), "warning")


def test_section_without_code_warns():
    text = "# demo\n\nA tool that does a thing well.\n\n## Installation\n\nUse pip.\n\n## Usage\n\n```\ndemo\n```\n"
    found = [f for f in rl.lint(text) if f.rule == "install"]
    assert found and found[0].severity == "warning"


def test_quick_start_counts_as_install_section():
    text = GOOD.replace("## Installation\n\n```bash\npip install demo\n```\n\n", "")
    assert "install" not in rules(rl.lint(text))


def test_late_first_code_block_warns():
    filler = "\n".join(f"Line {i} of prose." for i in range(80))
    text = GOOD.replace("## Installation", filler + "\n\n## Installation")
    assert "scroll" in rules(rl.lint(text, max_scroll=60))


def test_broken_relative_link_and_alt_text(tmp_path):
    text = GOOD + "\n![](docs/shot.png)\n[guide](docs/guide.md#intro) [ok](https://example.com) [anchor](#faq)\n"
    findings = rl.lint(text, tmp_path)
    broken = [f.message for f in findings if f.rule == "broken-link"]
    assert any("docs/guide.md" in m for m in broken)
    assert any("docs/shot.png" in m for m in broken)
    assert not any("example.com" in m or "#faq" in m for m in broken)
    assert "alt-text" in rules(findings)


def test_headings_in_code_are_not_sections():
    text = "# demo\n\nA tool that does a thing well.\n\n```bash\n# Installation\npip install demo\n```\n"
    assert "install" in rules(rl.lint(text), "error")


def test_multiple_h1_and_placeholders():
    text = GOOD + "\n# Another title\n\nTODO: write more\n"
    found = rules(rl.lint(text))
    assert {"title", "placeholder"} <= found


def test_cli_exit_codes_and_json(tmp_path):
    write(tmp_path, "CONTRIBUTING.md")
    write(tmp_path, "LICENSE")
    good = write(tmp_path, "README.md", GOOD)
    proc = run_script("readme-writer", "readme_lint", str(good), "--json")
    assert proc.returncode == 0
    assert json.loads(proc.stdout)["counts"]["error"] == 0
    warn_only = write(tmp_path, "W.md", GOOD.replace("## FAQ\n\n**Why?** Because.\n\n", "").replace("[![CI]", "[CI]"))
    assert run_script("readme-writer", "readme_lint", str(warn_only)).returncode == 0
    assert run_script("readme-writer", "readme_lint", str(warn_only), "--strict").returncode == 1
    bad = write(tmp_path, "BAD.md", "nothing\n")
    assert run_script("readme-writer", "readme_lint", str(bad)).returncode == 1
    assert run_script("readme-writer", "readme_lint", str(tmp_path / "missing.md")).returncode == 2


def test_any_matching_section_with_code_counts():
    text = GOOD.replace("## Quick start", "## Usage examples\n\nPlain prose.\n\n## Quick start")
    assert "quickstart" not in rules(rl.lint(text))


def test_anchor_list_counts_as_table_of_contents():
    sections = "".join(f"## Section {i}\n\ntext\n\n" for i in range(9))
    assert "toc" in rules(rl.lint(GOOD + sections))
    toc = "".join(f"- [Section {i}](#section-{i})\n" for i in range(9))
    assert "toc" not in rules(rl.lint(GOOD.replace("## Installation", toc + "\n## Installation") + sections))


def test_bold_pitch_sentence_is_split():
    text = GOOD.replace(
        "demo is a command-line tool that turns messy CSV files into clean JSON for data teams.",
        "**demo turns messy CSV files into clean JSON.** " + "More detail here. " * 20,
    )
    assert "pitch" not in rules(rl.lint(text))


def test_heading_slug_matches_github():
    assert rl.heading_slug("Quick start") == "quick-start"
    assert rl.heading_slug("What's `new` in v2.0?") == "whats-new-in-v20"
    assert rl.heading_slug("[Docs](https://x.example) & FAQ") == "docs--faq"
    assert rl.heading_slug("snake_case_name") == "snake_case_name"
    assert rl.heading_slug("Café") == "café"


def test_broken_anchor_links(tmp_path):
    write(tmp_path, "CONTRIBUTING.md")
    write(tmp_path, "LICENSE")
    toc = (
        "- [Installation](#installation)\n"
        "- [Usage](#usage)\n"  # renamed to Quick start: broken
        "- [FAQ](#faq)\n"
        "- [Second FAQ](#faq-1)\n"  # duplicate heading suffix
        "- [Legacy](#legacy-anchor)\n"  # HTML anchor
        "- [Encoded](#quick%20start)\n"  # not GitHub's slug: broken
    )
    text = GOOD.replace("## Installation", toc + "\n## Installation", 1)
    text += '\n## FAQ\n\nMore.\n\n<a name="legacy-anchor"></a>\n\n```md\n[in code](#nowhere)\n```\n'
    findings = [f for f in rl.lint(text, tmp_path) if f.rule == "broken-anchor"]
    assert [f.message.split("'")[1] for f in findings] == ["#usage", "#quick%20start"]
    assert all(f.severity == "error" for f in findings)


def test_file_links_with_fragments_are_not_anchor_checked(tmp_path):
    write(tmp_path, "CONTRIBUTING.md")
    write(tmp_path, "LICENSE")
    text = GOOD.replace("See [CONTRIBUTING.md](CONTRIBUTING.md).", "See [setup](CONTRIBUTING.md#setup).")
    assert rl.lint(text, tmp_path) == []
