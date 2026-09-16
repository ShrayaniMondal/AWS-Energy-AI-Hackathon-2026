from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.configure_aws_target import build_target, write_target


def test_build_target_validates_account_and_region() -> None:
    assert build_target("123456789012", "us-east-1") == {
        "name": "hackathon",
        "account": "123456789012",
        "region": "us-east-1",
    }

    with pytest.raises(ValueError, match="12 digits"):
        build_target("123", "us-east-1")
    with pytest.raises(ValueError, match="AWS region"):
        build_target("123456789012", "east")


def test_write_target_creates_agentcore_target(tmp_path: Path) -> None:
    output = tmp_path / "agentcore" / "aws-targets.json"
    write_target(output, build_target("123456789012", "us-west-2"))

    assert json.loads(output.read_text(encoding="utf-8")) == [
        {"name": "hackathon", "account": "123456789012", "region": "us-west-2"}
    ]
