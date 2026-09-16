Implement the requested GeoDrill Risk Copilot deliverable using the repository contract.

Before editing, read `AGENTS.md`, `teams.md`, `docs/hpc-catalog-feature-contract.md`, `docs/architecture/solution.md`, and the relevant tests. State the owner, acceptance criterion, and catalog/export contract you are implementing. Use strict test-first development. Preserve row/file provenance in every output and keep synthetic/calibrated limitations explicit.

Prioritize this vertical slice order:

1. deterministic local behavior;
2. catalog-compatible JSON/CSV contract and provenance;
3. Streamlit journey;
4. AgentCore runtime integration;
5. AWS deployment evidence;
6. judge-facing evidence update.

Run the smallest focused check after each change and `make validate` before stopping. Do not claim deployment without a real runtime identifier and successful invocation. Return only: changed files, validation output, evidence produced, catalog/dashboard compatibility, and remaining blockers.
