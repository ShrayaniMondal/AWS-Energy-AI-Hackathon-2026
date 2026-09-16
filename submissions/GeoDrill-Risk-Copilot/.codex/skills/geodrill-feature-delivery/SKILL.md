---
name: geodrill-feature-delivery
description: Deliver grounded GeoDrill features through stable contracts.
version: 0.1.0
author: GeoDrill Team, Codex
license: MIT
platforms: [linux, macos, windows]
metadata:
  codex:
    tags: [energy, provenance, testing]
---

# GeoDrill Feature Delivery

Deliver one team-owned feature without breaking the shared catalog, scoring, dashboard, or AgentCore contracts.

## When to Use

- Implementing a deliverable listed in `teams.md`.
- Changing catalog, analysis, scoring, chat, dashboard, or runtime behavior.
- Integrating another team member's JSON or CSV contract.

## Procedure

1. Read `teams.md`, `docs/architecture/solution.md`, `docs/hpc-catalog-feature-contract.md`, and the nearest tests.
2. Name the feature owner, accepted input, exported output, and downstream consumer before editing.
3. Write a failing test for one end-to-end behavior and confirm the failure is caused by missing behavior.
4. Implement the smallest behavior that passes while preserving `run_id`, catalog IDs, source row/file, artifact path, and synthetic-data status where available.
5. Export machine-readable JSON or CSV using the same fields shown to users.
6. Document the business decision enabled, the evidence used, and what the data cannot support.
7. Run the focused test, then `make validate` and one deterministic demo.
8. Update `docs/judging/evidence-map.md` only with evidence that now exists.

## Pitfalls

- Never join Corpus A and Corpus B by well identifier; their key spaces differ.
- Never hide a failed evidence lookup behind a plausible narrative.
- Never make a visualization-only state that cannot be exported and reloaded.
- Never call configuration or a dry run a deployed cloud feature.

## Verification

The feature is complete when tests pass, the accepted journey runs, exported data reloads after restart, provenance is visible, and the evidence map points to actual artifacts.
