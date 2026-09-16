# Codex Repository Adapter

Read and follow the root `AGENTS.md` before acting. It is the authoritative implementation contract.

Default flow:

1. Inspect the relevant implementation, tests, `teams.md`, `docs/hpc-catalog-feature-contract.md`, and architecture/evidence docs.
2. Keep work within the assigned owner boundary unless an interface change is coordinated.
3. Write the smallest failing test for the requested behavior.
4. Implement one end-to-end vertical slice with explicit provenance and catalog-compatible JSON/CSV exports.
5. Run the focused test, then `make validate`.
6. Report changed files, exact command results, deployment evidence, and remaining risks.

Every feature must preserve catalog join keys (`run_id`, project/site/dataset/dimension/segment/file IDs), source rows, and artifact paths when available, so CLI, dashboard, and AgentCore outputs can feed advanced visualization without recomputing private state.

Do not add other assistant-specific adapters. Claude artifacts in this repository are for judging and deployment review only.
