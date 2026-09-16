from __future__ import annotations

import json
from pathlib import Path

from aws_ai_energy.validation import evaluate_repository


def _touch(root: Path, relative: str, content: str = "x") -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_evaluate_repository_maps_all_judging_dimensions(tmp_path: Path) -> None:
    required = {
        "README.md": "GeoDrill",
        "teams.md": "Aditya Shrayani Rongrong Yuxin",
        "CLAUDE.md": "judge context",
        "docs/Use-Case-1-Drilling-Report-Analysis-Agent.md": "Drilling",
        "docs/proposal/drilling-hazard-copilot.md": "hazard",
        "docs/hpc-catalog-feature-contract.md": "datasetid segmentid fileid",
        "docs/judging/evidence-map.md": "evidence",
        "generate/analyze_catalog.py": "subsurface.cli",
        "src/aws_ai_energy/generate/seismic_catalog.py": "filesystemid",
        "src/aws_ai_energy/subsurface/scoring.py": "hazard_score",
        "src/aws_ai_energy/subsurface/export.py": "manifest",
        "src/aws_ai_energy/dashboard.py": "physical_data_provenance",
        "agentcore/agentcore.json": json.dumps({"runtimes": [{"name": "geodrill_copilot"}]}),
        "agentcore/cdk/README.md": "AgentCore",
        "agentcore/.llm-context/agentcore.ts": "AgentCoreProjectSpec",
        "agentcore_app/main.py": "BedrockAgentCoreApp",
        "Hackathon/use-case-1/data/npt_incident_log.csv": "incident_id",
        "Hackathon/use-case-1/data/formation_tops.csv": "well_id",
        "Hackathon/use-case-1/data/drilling_plan.csv": "well_id",
    }
    for relative, content in required.items():
        _touch(tmp_path, relative, content)

    report = evaluate_repository(tmp_path)

    assert report["contract_valid"] is True
    assert set(report["dimensions"]) == {
        "use_case_solution",
        "usable_interface",
        "agent_collaboration",
        "agentcore_deployment",
        "dataset_grounding",
    }
    assert all(item["passed"] for item in report["dimensions"].values())
    assert report["cloud_deployment_verified"] is False


def test_evaluate_repository_fails_closed_on_missing_evidence(tmp_path: Path) -> None:
    _touch(tmp_path, "README.md")

    report = evaluate_repository(tmp_path)

    assert report["contract_valid"] is False
    assert report["dimensions"]["dataset_grounding"]["passed"] is False
    assert report["missing"]
