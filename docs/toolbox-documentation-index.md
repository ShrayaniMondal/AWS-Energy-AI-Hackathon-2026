# Toolbox Documentation Index

`aws_ai_energy.toolbox_docs` builds a deterministic JSON index for code-helper
and agent support. It scrapes:

- repository Markdown such as `README.md`, `docs/`, and Hackathon notes;
- public Python module docstrings;
- public Python function/class docstrings.

Private Python symbols beginning with `_` are excluded so callers see the
supported toolbox surface rather than implementation internals.

## Build

```bash
.venv/bin/python -m aws_ai_energy.toolbox_docs \
  --root . \
  --output outputs/toolbox-index.json \
  --validate-skills
```

The output includes `schema_version`, `document_count`, `chunk_count`,
`source_digest`, and stable chunks with `source`, `kind`, `symbol`, `title`, and
`text`.

## Skill Validation

`--validate-skills` checks repository-local `.codex/skills/*/SKILL.md` files for
YAML frontmatter with `name`, `description`, and `version`, plus operational
sections for when to use the skill and how to verify it. Missing or malformed
skills are reported as actionable errors.

## Coverage Gate

`make test-coverage` runs the full test suite under coverage and writes
`coverage.xml`. The current CI-style floor is 80% line/branch coverage; this is
a measured readiness guard, not a claim of 100% coverage.
