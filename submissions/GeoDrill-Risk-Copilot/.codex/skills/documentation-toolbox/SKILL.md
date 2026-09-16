---
name: documentation-toolbox
description: Index repository guidance for grounded caller support.
version: 0.1.0
author: GeoDrill Team, Codex
license: MIT
platforms: [linux, macos, windows]
metadata:
  codex:
    tags: [documentation, retrieval, provenance]
---

# Documentation Toolbox

Build and maintain the deterministic repository index used by local tools and AgentCore callers. The index is a citation layer, not a source of new domain claims.

## When to Use

- Adding or restructuring project documentation.
- Adding a public Python API, docstring, or caller-facing contract.
- Changing the centralized toolbox index or retrieval behavior.
- Reviewing whether business and provenance guidance is discoverable.

Do not use it to index generated outputs, credentials, virtual environments, or private implementation comments.

## Procedure

1. Read `docs/toolbox-helper.md`, `docs/hpc-catalog-feature-contract.md`, and the affected public APIs.
2. State the caller question and the exact repository evidence that should answer it.
3. Add or update headings and public docstrings with purpose, inputs, outputs, limitations, and provenance.
4. Keep chunks independently understandable; do not rely on an earlier section to define critical identifiers.
5. Run `PYTHONPATH=src python -m aws_ai_energy.toolbox_docs --root . --validate-skills --output artifacts/toolbox-index.json` and inspect the emitted chunk count and digest.
6. Use `ToolboxIndex.search()` for a representative caller question and verify every result has a repository-relative path and line range.
7. Run `make validate`; completion requires the full gate to pass.

## Pitfalls

- Do not duplicate PDF text when a maintained Markdown twin exists.
- Do not describe screening ranks as calibrated predictions.
- Do not commit the generated index under `artifacts/`; rebuild it from source.
- Do not index private functions merely to inflate toolbox coverage.

## Verification

- `PYTHONPATH=src python -m aws_ai_energy.toolbox_docs --root . --validate-skills --output artifacts/toolbox-index.json`
- `PYTHONPATH=src python -c "from aws_ai_energy.toolbox_docs import build_toolbox_index; print(build_toolbox_index('.').search('business value drilling NPT provenance'))"`
- `make validate`

All commands must exit zero, and search results must include exact source paths and line ranges.
