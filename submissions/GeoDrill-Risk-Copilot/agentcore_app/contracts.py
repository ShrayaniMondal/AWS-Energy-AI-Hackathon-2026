from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class InvocationError(ValueError):
    """Raised when an AgentCore invocation payload or local artifact is invalid."""


def extract_prompt(payload: Any) -> str:
    if not isinstance(payload, dict):
        raise InvocationError("invocation payload must be a JSON object")
    prompt = payload.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise InvocationError("prompt must be a non-empty string")
    return prompt.strip()


def load_ranked_prospects(analysis_dir: Path | str, *, limit: int = 10) -> dict[str, Any]:
    if limit < 1 or limit > 100:
        raise InvocationError("limit must be between 1 and 100")

    run_dir = _latest_analysis_run(Path(analysis_dir))
    targets_path = run_dir / "reservoir_targets.json"
    if not targets_path.is_file():
        raise InvocationError(f"reservoir targets JSON not found: {targets_path}")
    with targets_path.open(encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise InvocationError(f"{targets_path} must contain a JSON array")

    return {
        "analysis_run": run_dir.name,
        "count": min(limit, len(rows)),
        "prospects": rows[:limit],
        "notice": (
            "Reservoir targets are deterministic screening ranks from generated "
            "synthetic seismic data, not calibrated predictions."
        ),
    }


def _latest_analysis_run(root: Path) -> Path:
    if not root.is_dir():
        raise InvocationError(f"analysis directory not found: {root}")
    candidates = [
        path for path in root.iterdir() if path.is_dir() and (path / "manifest.json").is_file()
    ]
    if not candidates:
        raise InvocationError(f"no analysis manifest found under {root}")
    return sorted(candidates, key=lambda path: path.name)[-1]
