Audit repository documentation and Python public API documentation without editing first.

Read `AGENTS.md`, every `.codex/skills/*/SKILL.md`, `README.md`, `teams.md`, all Markdown under `docs/`, `Hackathon/use-case-1/`, `generate/`, and `scripts/SCRIPTS.md`, then inspect public Python APIs under `src/`, `scripts/`, and `agentcore_app/`.

Check:

1. domain correctness and contradictions;
2. business decision and measurable value;
3. stable inputs, outputs, errors, and limitations;
4. file/row/artifact provenance;
5. centralized toolbox scrapeability;
6. AgentCore/Bedrock readiness without overstated deployment claims;
7. Codex skill syntax, paths, and verification commands.

Return blockers first with exact paths, then high-leverage improvements. After approval, patch minimally and run `PYTHONPATH=src python -m aws_ai_energy.toolbox_docs --root . --validate-skills` plus `make validate`.
