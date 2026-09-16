from __future__ import annotations

import json
from pathlib import Path

from aws_ai_energy.toolbox_docs import (
    build_toolbox_index,
    validate_codex_skills,
    write_toolbox_index,
)


def test_build_toolbox_index_scrapes_markdown_and_public_python_docs(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "src").mkdir()
    (tmp_path / "docs" / "value.md").write_text(
        "# Business Value\n\nReduce drilling NPT with cited evidence.\n", encoding="utf-8"
    )
    (tmp_path / "src" / "tool.py").write_text(
        '"""Catalog tools for grounded decisions."""\n\n'
        'def rank_targets() -> list[str]:\n'
        '    """Rank reservoir targets while preserving file provenance."""\n'
        '    return []\n\n'
        'def _private() -> None:\n'
        '    """Not part of the caller toolbox."""\n',
        encoding="utf-8",
    )
    staged = tmp_path / "agentcore" / "runtime" / "staging" / "vendor.py"
    staged.parent.mkdir(parents=True)
    staged.write_text('"""Third-party staged dependency."""\n', encoding="utf-8")

    index = build_toolbox_index(tmp_path)

    assert index.schema_version == "1.0"
    assert {chunk.kind for chunk in index.chunks} == {"markdown", "python_module", "python_api"}
    assert any(chunk.symbol == "rank_targets" for chunk in index.chunks)
    assert not any(chunk.symbol == "_private" for chunk in index.chunks)
    assert not any("staging" in chunk.source for chunk in index.chunks)
    assert all(
        chunk.start_line is not None and chunk.end_line is not None for chunk in index.chunks
    )
    result = index.search("reduce drilling NPT evidence", top_k=1)[0]
    assert result.chunk.source == "docs/value.md"
    assert result.score > 0


def test_write_toolbox_index_is_deterministic_and_machine_readable(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("# Toolbox\n\nGrounded support.", encoding="utf-8")
    index = build_toolbox_index(tmp_path)
    output = tmp_path / "artifacts" / "toolbox-index.json"

    write_toolbox_index(index, output)
    first = output.read_bytes()
    write_toolbox_index(index, output)

    assert output.read_bytes() == first
    payload = json.loads(first)
    assert payload["document_count"] == 1
    assert len(payload["source_digest"]) == 64
    assert payload["chunks"][0]["source"] == "README.md"


def test_validate_codex_skills_reports_actionable_errors(tmp_path: Path) -> None:
    good = tmp_path / ".codex" / "skills" / "delivery" / "SKILL.md"
    good.parent.mkdir(parents=True)
    good.write_text(
        "---\n"
        "name: delivery\n"
        "description: Deliver a grounded vertical slice.\n"
        "version: 0.1.0\n"
        "---\n"
        "# Delivery\n\n## When to Use\n\nUse for feature delivery.\n"
        "## Verification\n\nRun the repository gate.\n",
        encoding="utf-8",
    )

    assert validate_codex_skills(tmp_path) == []

    bad = tmp_path / ".codex" / "skills" / "broken" / "SKILL.md"
    bad.parent.mkdir(parents=True)
    bad.write_text("# Missing frontmatter\n", encoding="utf-8")
    issues = validate_codex_skills(tmp_path)
    assert any("frontmatter" in issue for issue in issues)
