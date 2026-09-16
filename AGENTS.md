# GeoDrill Risk Copilot — Codex Operating Guide

This repository uses Codex as its implementation assistant. Do not add Gemini, Hermes, or Claude development adapters. `CLAUDE.md` is judge/deployment context, not a second implementation workflow.

## Mission

Answer one decision question with traceable evidence:

> Where are attractive reservoir targets, where are fault/fracture drilling hazards, and which catalog files and drilling records support the recommendation?

Build one demonstrable path: seeded seismic catalog -> interpreted subsurface evidence -> risk-ranked prospects -> chat/heatmap dashboard -> JSON exports -> AgentCore runtime.

## Read First

1. `README.md`
2. `teams.md`
3. `docs/architecture/solution.md`
4. `docs/judging/evidence-map.md`
5. The nearest tests for the component you will change

## Non-negotiable Contracts

- Preserve row-level provenance. Every derived recommendation must retain catalog row/file identifiers and drilling evidence locators.
- Label generated seismic data as synthetic and scores as screening ranks, not calibrated predictions.
- Do not join the narrative and tabular DDR corpora by well identifier; their identifier spaces differ.
- Keep feature ownership boundaries in `teams.md`; coordinate interface changes before crossing them.
- Write a failing test before changing behavior, then run the focused test and `make validate`.
- Never commit AWS credentials, API keys, generated outputs, or deployment state.
- Never claim cloud deployment from configuration alone. Capture stack/runtime IDs and smoke-test output after a real deployment.
- `agentcore/agentcore.json` is the AgentCore source of truth. Do not hand-edit generated code under `agentcore/cdk/`.

## Commands

- `make bootstrap` — install development, dashboard, and AgentCore dependencies.
- `make demo` — generate deterministic catalog and full analysis evidence.
- `make dashboard` — start the Streamlit dashboard on port 8501.
- `make validate` — lint, types, tests, Claude-readiness contract, and AgentCore schema.
- `make agentcore-dev` — run the AgentCore backend locally.
- `make agentcore-deploy-dry-run` — preview deployment after configuring the `hackathon` target.

## Definition of Done

A feature is done only when its accepted journey runs, tests cover success and failure paths, exported JSON is stable, provenance is visible, documentation names limitations, and the relevant validation targets pass. Cloud work additionally requires a deployed endpoint and a recorded invocation; presentation work requires a resettable offline demo.
