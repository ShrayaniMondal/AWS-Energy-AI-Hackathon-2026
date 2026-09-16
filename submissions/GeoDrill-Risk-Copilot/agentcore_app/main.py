from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

try:
    from agentcore_app.contracts import InvocationError, extract_prompt, load_ranked_prospects
except ModuleNotFoundError:  # AgentCore CodeZip flattens the codeLocation at package root.
    from contracts import (  # type: ignore[import-not-found,no-redef]
        InvocationError,
        extract_prompt,
        load_ranked_prospects,
    )

try:
    from bedrock_agentcore.runtime import BedrockAgentCoreApp
except ImportError:
    F = TypeVar("F", bound=Callable[..., Any])

    class BedrockAgentCoreApp:  # type: ignore[no-redef]
        """Local fallback matching the small decorator surface used in tests."""

        def entrypoint(self, func: F) -> F:
            return func

        def run(self) -> None:
            return None


app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = extract_prompt(payload)
    analysis_dir = Path(str(payload.get("analysis_dir", "outputs/hazard_demo/analysis")))
    limit = int(payload.get("limit", 5))
    try:
        prospects = load_ranked_prospects(analysis_dir, limit=limit)
    except InvocationError as error:
        return {"prompt": prompt, "error": str(error), "prospects": []}
    return {
        "prompt": prompt,
        "answer": "Ranked reservoir prospects loaded from the latest grounded export.",
        **prospects,
    }


if __name__ == "__main__":
    app.run()
