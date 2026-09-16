from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DIMENSION_CHECKS: dict[str, tuple[tuple[str, str], ...]] = {
    "use_case_solution": (
        ("docs/Use-Case-1-Drilling-Report-Analysis-Agent.md", "Drilling"),
        ("docs/proposal/drilling-hazard-copilot.md", "hazard"),
        ("src/aws_ai_energy/subsurface/scoring.py", "hazard_score"),
    ),
    "usable_interface": (
        ("README.md", "GeoDrill"),
        ("generate/analyze_catalog.py", "subsurface.cli"),
    ),
    "agent_collaboration": (
        ("teams.md", "Aditya"),
        ("teams.md", "Shrayani"),
        ("teams.md", "Rongrong"),
        ("teams.md", "Yuxin"),
        ("CLAUDE.md", "judge"),
    ),
    "agentcore_deployment": (
        ("agentcore/cdk/README.md", "AgentCore"),
        ("agentcore/.llm-context/agentcore.ts", "AgentCoreProjectSpec"),
    ),
    "dataset_grounding": (
        ("docs/hpc-catalog-feature-contract.md", "datasetid"),
        ("docs/hpc-catalog-feature-contract.md", "segmentid"),
        ("docs/hpc-catalog-feature-contract.md", "fileid"),
        ("src/aws_ai_energy/generate/seismic_catalog.py", "filesystemid"),
        ("src/aws_ai_energy/subsurface/export.py", "manifest"),
    ),
}


def _contains(root: Path, relative: str, token: str) -> bool:
    path = root / relative
    if not path.is_file():
        return False
    return token.lower() in path.read_text(encoding="utf-8", errors="ignore").lower()


def _cloud_deployment_verified(root: Path) -> bool:
    state_path = root / "agentcore" / ".cli" / "deployed-state.json"
    if not state_path.is_file():
        return False
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    text = json.dumps(state).lower()
    return "runtime" in text and ("endpoint" in text or "arn" in text)


def evaluate_repository(root: Path) -> dict[str, Any]:
    """Evaluate the local repository against lightweight hackathon evidence checks."""
    root = root.resolve()
    dimensions: dict[str, dict[str, Any]] = {}
    missing: list[dict[str, str]] = []

    for dimension, checks in DIMENSION_CHECKS.items():
        failed: list[dict[str, str]] = []
        for relative, token in checks:
            if not _contains(root, relative, token):
                item = {"path": relative, "token": token}
                failed.append(item)
                missing.append({"dimension": dimension, **item})
        dimensions[dimension] = {
            "passed": not failed,
            "checks": len(checks),
            "missing": failed,
        }

    return {
        "contract_valid": not missing,
        "dimensions": dimensions,
        "missing": missing,
        "cloud_deployment_verified": _cloud_deployment_verified(root),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate GeoDrill submission evidence.")
    parser.add_argument(
        "--repo",
        type=Path,
        default=Path.cwd(),
        help="Repository root to validate.",
    )
    args = parser.parse_args(argv)

    report = evaluate_repository(args.repo)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["contract_valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
