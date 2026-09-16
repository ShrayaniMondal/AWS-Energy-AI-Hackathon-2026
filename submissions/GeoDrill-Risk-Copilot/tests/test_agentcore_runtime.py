from __future__ import annotations

import json
from pathlib import Path

import pytest

from agentcore_app.contracts import (
    InvocationError,
    extract_prompt,
    load_ranked_prospects,
)


def test_extract_prompt_accepts_only_nonempty_string() -> None:
    assert extract_prompt({"prompt": "Where are the safest targets?"}) == (
        "Where are the safest targets?"
    )

    with pytest.raises(InvocationError, match="non-empty string"):
        extract_prompt({"prompt": "  "})
    with pytest.raises(InvocationError, match="JSON object"):
        extract_prompt("prompt")  # type: ignore[arg-type]


def test_load_ranked_prospects_returns_bounded_grounded_rows(tmp_path: Path) -> None:
    run = tmp_path / "run_002"
    run.mkdir()
    rows = [
        {
            "row": index,
            "target_score": 1.0 - index / 10,
            "confidence_score": 0.8,
            "fileid": 10,
        }
        for index in range(1, 5)
    ]
    (run / "reservoir_targets.json").write_text(json.dumps(rows), encoding="utf-8")
    (run / "manifest.json").write_text("{}", encoding="utf-8")

    result = load_ranked_prospects(tmp_path, limit=2)

    assert result["analysis_run"] == "run_002"
    assert result["count"] == 2
    assert result["prospects"] == rows[:2]
    assert "screening" in result["notice"].lower()


def test_load_ranked_prospects_rejects_invalid_limit(tmp_path: Path) -> None:
    with pytest.raises(InvocationError, match="between 1 and 100"):
        load_ranked_prospects(tmp_path, limit=0)
