from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

AWS_REGION_PATTERN = re.compile(r"^[a-z]{2}-[a-z]+-[0-9]$")


def build_target(account: str, region: str) -> dict[str, str]:
    if not re.fullmatch(r"\d{12}", account):
        raise ValueError("AWS account must be exactly 12 digits")
    if not AWS_REGION_PATTERN.fullmatch(region):
        raise ValueError("AWS region must look like us-east-1")
    return {"name": "hackathon", "account": account, "region": region}


def write_target(path: Path | str, target: dict[str, str]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        json.dump([target], handle, indent=2, sort_keys=True)
        handle.write("\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write AgentCore AWS target metadata.")
    parser.add_argument("account", help="12-digit AWS account id.")
    parser.add_argument("region", help="AWS region, for example us-east-1.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("agentcore/aws-targets.json"),
        help="Output JSON path. Defaults to agentcore/aws-targets.json.",
    )
    args = parser.parse_args(argv)
    target: dict[str, str] = build_target(args.account, args.region)
    write_target(args.output, target)
    print(json.dumps({"written": str(args.output), "target": target}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
